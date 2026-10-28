// tb_accel.cpp - Verilator: accel_top (the bz3 unit + sequencer + SRAM + FSM) runs one tree from the HBM and back,
// against the CPU baseline. Usage: Vaccel_top <prog dir> [hbm_latency] [hbm_bw_per_cycle]
//   prog dir (build_prog.py): tile/, top/ (ctrl.hex, desc_<k>.hex, meta.txt), vec.hex, meta.txt
// The HBM model: a read request is accepted when fewer than BW are accepted this cycle, its data returns LAT cycles
// later; writes are accepted BW per cycle and land immediately. Merkle: the leaves are in the HBM at hbm_leaf; the root
// is read back from hbm_root. GGM: the seed at hbm_root; the 2^SZ leaves are read back from hbm_leaf.
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <deque>
#include <fstream>
#include <sstream>
#include "verilated.h"
#include "Vaccel_top.h"
#include "Vaccel_top___024root.h"
typedef Vaccel_top DUT;
static DUT* dut; static uint64_t tcyc = 0;
static void tick() { dut->clk = 0; dut->eval(); dut->clk = 1; dut->eval(); tcyc++; }
struct V256 { uint32_t w[8]; };
static std::map<std::string, std::string> meta(const std::string& p) {
    std::map<std::string, std::string> m; std::ifstream f(p); std::string l;
    while (std::getline(f, l)) { auto s = l.find(' '); if (s != std::string::npos) m[l.substr(0, s)] = l.substr(s + 1); }
    return m;
}
static std::vector<std::string> hexlines(const std::string& p) {
    std::vector<std::string> v; std::ifstream f(p); std::string l; while (std::getline(f, l)) if (!l.empty()) v.push_back(l); return v;
}
static void hex2words(const std::string& h, uint32_t* w, int nw) {        // little-endian words from a hex string
    for (int i = 0; i < nw; i++) {
        uint32_t v = 0; int end = (int)h.size() - 8 * i;
        for (int j = std::max(0, end - 8); j < end; j++) { char c = h[j]; v = (v << 4) | (uint32_t)(c <= '9' ? c - '0' : (c | 32) - 'a' + 10); }
        w[i] = v;
    }
}
static void load_prog(const std::string& dir, int bank) {
    auto c = hexlines(dir + "/ctrl.hex");
    for (size_t i = 0; i < c.size(); i++) { uint32_t w[10]; hex2words(c[i], w, 10); for (int j = 0; j < 10; j++) dut->rootp->accel_top__DOT__u_prog__DOT__cmem[bank][i][j] = w[j]; }
    const int nb[16] = {7, 4, 3, 1, 2, 1, 1, 7, 4, 3, 1, 2, 1, 1, 1, 1};
    for (int k = 0; k < 16; k++) {
        auto d = hexlines(dir + "/desc_" + std::to_string(k) + ".hex");
        for (size_t g = 0; g * nb[k] < d.size(); g++) {
            uint32_t w[7 * 4]; memset(w, 0, sizeof w);
            for (int b = 0; b < nb[k]; b++) hex2words(d[g * nb[k] + b], w + 4 * b, 4);   // 104 bits = 3.25 words; 4 words per slot (128 bits) -> packed at 104?
            // dmem words are 32-bit chunks of the 728-bit group word: descriptor b occupies bits 104 b .. 104 b + 103
            uint32_t packed[23]; memset(packed, 0, sizeof packed);
            for (int b = 0; b < nb[k]; b++) for (int bit = 0; bit < 104; bit++) {
                int src = bit; int dst = 104 * b + bit;
                if ((w[4 * b + src / 32] >> (src % 32)) & 1) packed[dst / 32] |= 1u << (dst % 32);
            }
            for (int j = 0; j < 23; j++) dut->rootp->accel_top__DOT__u_prog__DOT__dmem[bank][k][g][j] = packed[j];
        }
    }
}
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 2) { printf("usage: Vaccel_top <prog dir> [lat] [bw]\n"); return 1; }
    std::string dir = argv[1]; int LAT = argc > 2 ? atoi(argv[2]) : 60; int BW = argc > 3 ? atoi(argv[3]) : 4;
    auto m = meta(dir + "/meta.txt"); bool ggm = m["req"] == "ggm"; int SZ = atoi(m["sz"].c_str()), TK = atoi(m["tk"].c_str());
    int ndata = atoi(m["ndata"].c_str()), nexp = atoi(m["nexp"].c_str());
    auto vec = hexlines(dir + "/vec.hex"); std::vector<uint32_t> words(vec.size());
    for (size_t i = 0; i < vec.size(); i++) hex2words(vec[i], &words[i], 1);
    dut = new DUT; dut->clk = 0; dut->rst = 1; dut->start = 0; dut->rd_ready = 0; dut->rsp_valid = 0; dut->wr_ready = 0;
    load_prog(dir + "/tile", 0); load_prog(dir + "/top", 1);
    const uint32_t HBM_LEAF = 0, HBM_INT = 1u << 26, HBM_ROOT = 3u << 26;
    std::map<uint32_t, V256> hbm;                                           // byte address (32 B aligned) -> value
    if (!ggm) for (int i = 0; i < (1 << SZ); i++) { V256 v; for (int j = 0; j < 8; j++) v.w[j] = words[8 * i + j]; hbm[HBM_LEAF + 32 * i] = v; }
    else { V256 v; for (int j = 0; j < 8; j++) v.w[j] = words[j]; hbm[HBM_ROOT] = v; }
    dut->cfg_ggm = ggm; dut->cfg_sz = SZ; dut->cfg_tk = TK;
    dut->cfg_ncyc_tile = atoi(m["tile_cycles"].c_str()); dut->cfg_ncyc_top = atoi(m["top_cycles"].c_str());
    dut->cfg_hbm_leaf = HBM_LEAF; dut->cfg_hbm_int = HBM_INT; dut->cfg_hbm_root = HBM_ROOT;
    tick(); tick(); dut->rst = 0; tick();
    // HBM model
    struct Req { uint64_t due; uint32_t addr; uint16_t tag; };
    std::deque<Req> rq; uint64_t nrd = 0, nwr = 0, rd_busy = 0;
    dut->start = 1; tick(); dut->start = 0;
    bool done = false; uint64_t t0 = tcyc;
    while (!done && tcyc - t0 < 50000000) {
        // responses due this cycle (one per cycle)
        dut->rsp_valid = 0;
        if (!rq.empty() && rq.front().due <= tcyc) {
            Req q = rq.front(); rq.pop_front(); auto it = hbm.find(q.addr); V256 v; memset(&v, 0, sizeof v);
            if (it != hbm.end()) v = it->second;
            for (int j = 0; j < 8; j++) dut->rsp_data[j] = v.w[j];
            dut->rsp_tag = q.tag; dut->rsp_valid = 1;
        }
        dut->rd_ready = (int)rq.size() < BW * LAT ? 1 : 0;                     // BW requests per cycle in flight over LAT
        dut->wr_ready = 1;
        dut->eval();
        if (dut->rd_valid && dut->rd_ready) { rq.push_back({tcyc + (uint64_t)LAT, dut->rd_addr, (uint16_t)dut->rd_tag}); nrd++; }
        if (dut->wr_valid && dut->wr_ready) { V256 v; for (int j = 0; j < 8; j++) v.w[j] = dut->wr_data[j]; hbm[dut->wr_addr] = v; nwr++; }
        if (!rq.empty()) rd_busy++;
        if (getenv("TRACE")) {
            uint32_t fin = dut->rootp->accel_top__DOT__u_seq__DOT__fin, iss = dut->rootp->accel_top__DOT__u_seq__DOT__issue;
            if (fin || iss || dut->wr_valid) printf("t %llu pc %u issue %04x fin %04x wr_valid %d wr_addr %08x st %d
", (unsigned long long)(tcyc - t0), dut->dbg_pc, iss, fin, dut->wr_valid, dut->wr_addr, (int)dut->rootp->accel_top__DOT__st);
        }
        tick();
        if (dut->done) done = true;
    }
    if (!done) { printf("TIMEOUT\n"); return 1; }
    int bad = 0;
    if (!ggm) {
        auto it = hbm.find(HBM_ROOT); if (it == hbm.end()) { printf("root not written\n"); bad = 8; }
        else for (int j = 0; j < 8; j++) if (it->second.w[j] != words[ndata + j]) bad++;
        printf("Merkle 2^%d (tiles of 2^%d): root %s the CPU baseline (%s)\n", SZ, TK, bad ? "DIFFERS from" : "==", m["source"].c_str());
    } else {
        for (int i = 0; i < (1 << SZ); i++) {
            auto it = hbm.find(HBM_LEAF + 32 * i);
            for (int j = 0; j < 8; j++) { uint32_t g = it == hbm.end() ? 0xDEAD : it->second.w[j]; if (g != words[ndata + 8 * i + j]) bad++; }
        }
        printf("GGM depth %d (subtrees of 2^%d): %d leaves %s the CPU baseline (%s)\n", SZ, TK, 1 << SZ, bad ? "DIFFER from" : "==", m["source"].c_str());
    }
    printf("  cycles %u: compute %u, HBM reads in flight %u, overlap %u; HBM %llu reads, %llu writes (32 B), latency %d, %d per cycle; write FIFO high-water %u\n",
           dut->st_cycles, dut->st_compute, dut->st_fetch, dut->st_overlap, (unsigned long long)nrd, (unsigned long long)nwr, LAT, BW, dut->st_wpend_max);
    printf("SUMMARY: %s, %d mismatching words\n", dir.c_str(), bad);
    delete dut; return bad ? 1 : 0;
}
