//! p3mono - Plonky3's Monolith-31 (p3-monolith 0.8.0, width 16, 5 + 1 rounds) as a C-ABI DLL for the CPU baseline.
//! Merkle node = permutation(left || right)[0..8], the framing of dse/TOP/verify/compile_tree.py; the tree is built
//! level by level, each level split over a rayon pool of the requested size.
use std::sync::OnceLock;
use std::time::Instant;

use p3_field::{PrimeCharacteristicRing, PrimeField32};
use p3_mersenne_31::Mersenne31;
use p3_monolith::{MonolithBarsM31, MonolithMdsMatrixMersenne31, MonolithMersenne31};
use p3_symmetric::Permutation;
use rayon::prelude::*;

type Mono = MonolithMersenne31<MonolithMdsMatrixMersenne31<16, 5>, 16, 5>;

fn perm() -> &'static Mono {
    static P: OnceLock<Mono> = OnceLock::new();
    P.get_or_init(|| MonolithMersenne31::new(MonolithBarsM31, MonolithMdsMatrixMersenne31::<16, 5>::new()))
}

fn node(src: &[u32], dst: &mut [u32]) {
    let mut s: [Mersenne31; 16] = core::array::from_fn(|k| Mersenne31::from_u32(src[k]));
    perm().permute_mut(&mut s);
    for k in 0..8 {
        dst[k] = s[k].as_canonical_u32();
    }
}

/// One permutation (16 words in, 16 out), for the known-answer check.
#[no_mangle]
pub extern "C" fn p3_mono_perm(inp: *const u32, out: *mut u32) {
    let i = unsafe { std::slice::from_raw_parts(inp, 16) };
    let o = unsafe { std::slice::from_raw_parts_mut(out, 16) };
    let mut s: [Mersenne31; 16] = core::array::from_fn(|k| Mersenne31::from_u32(i[k]));
    perm().permute_mut(&mut s);
    for k in 0..16 {
        o[k] = s[k].as_canonical_u32();
    }
}

// ---- Poseidon2-M31 (p3-mersenne-31 default_mersenne31_poseidon2_16: width 16, x^5, 4 + 14 + 4 rounds) ----
type Pos2 = p3_mersenne_31::Poseidon2Mersenne31<16>;
fn pos2() -> &'static Pos2 {
    static Q: OnceLock<Pos2> = OnceLock::new();
    Q.get_or_init(p3_mersenne_31::default_mersenne31_poseidon2_16)
}
fn pnode(src: &[u32], dst: &mut [u32]) {
    let mut s: [Mersenne31; 16] = core::array::from_fn(|k| Mersenne31::from_u32(src[k]));
    pos2().permute_mut(&mut s);
    for k in 0..8 {
        dst[k] = s[k].as_canonical_u32();
    }
}
#[no_mangle]
pub extern "C" fn p3_pos2_perm(inp: *const u32, out: *mut u32) {
    let i = unsafe { std::slice::from_raw_parts(inp, 16) };
    let o = unsafe { std::slice::from_raw_parts_mut(out, 16) };
    let mut s: [Mersenne31; 16] = core::array::from_fn(|k| Mersenne31::from_u32(i[k]));
    pos2().permute_mut(&mut s);
    for k in 0..16 {
        o[k] = s[k].as_canonical_u32();
    }
}
#[no_mangle]
pub extern "C" fn p3_pos2_tree(log2: u32, reps: u32, threads: u32, leaves: *const u32, root: *mut u32) -> f64 {
    run_tree(pnode, log2, reps, threads, leaves, root)
}

/// Merkle tree over 2^log2 leaves (8 words each; leaves == NULL: generated), on `threads` threads. Writes the root
/// (8 words) to `root` if not NULL and returns ns per node averaged over `reps` (leaves restored outside the clock).
#[no_mangle]
pub extern "C" fn p3_mono_tree(log2: u32, reps: u32, threads: u32, leaves: *const u32, root: *mut u32) -> f64 {
    run_tree(node, log2, reps, threads, leaves, root)
}
fn run_tree(nodef: fn(&[u32], &mut [u32]), log2: u32, reps: u32, threads: u32, leaves: *const u32, root: *mut u32) -> f64 {
    let n = 1usize << log2;
    let start: Vec<u32> = if leaves.is_null() {
        let mut x: u64 = 0x9E3779B97F4A7C15 ^ log2 as u64;
        (0..n * 8)
            .map(|_| {
                x ^= x >> 12;
                x ^= x << 25;
                x ^= x >> 27;
                ((x.wrapping_mul(0x2545F4914F6CDD1D) >> 33) as u32) & 0x7FFF_FFFF
            })
            .collect()
    } else {
        unsafe { std::slice::from_raw_parts(leaves, n * 8) }.to_vec()
    };
    let pool = rayon::ThreadPoolBuilder::new().num_threads(threads.max(1) as usize).build().unwrap();
    let _ = perm();
    let mut a = vec![0u32; n * 8];
    let mut b = vec![0u32; n * 8];
    let mut ns = 0f64;
    for rep in 0..reps.max(1) {
        a.copy_from_slice(&start);
        let t0 = Instant::now();
        let mut m = n / 2;
        let (mut src, mut dst) = (&mut a, &mut b);
        while m >= 1 {
            {
                let s: &[u32] = &src[..m * 16];
                let d: &mut [u32] = &mut dst[..m * 8];
                pool.install(|| {
                    d.par_chunks_mut(8 * 64).enumerate().for_each(|(c, dc)| {
                        for (j, o) in dc.chunks_mut(8).enumerate() {
                            let i = c * 64 + j;
                            nodef(&s[16 * i..16 * i + 16], o);
                        }
                    })
                });
            }
            std::mem::swap(&mut src, &mut dst);
            m /= 2;
        }
        ns += t0.elapsed().as_nanos() as f64;
        if rep + 1 == reps.max(1) && !root.is_null() {
            unsafe { std::slice::from_raw_parts_mut(root, 8) }.copy_from_slice(&src[..8]);
        }
    }
    ns / (((n - 1) as f64) * reps.max(1) as f64)
}
