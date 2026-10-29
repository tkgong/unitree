// tb_unit18.cpp - Verilator: a hand-written unit (RTL/src) runs a compiled program (compile_tree.py trace=) closed loop,
// cycle by cycle. Per cycle: the controls; the lanes the program writes fresh; the lanes it copies from the previous
// output (here: the RTL's own previous output); at every node finish the lanes the result is read from are compared with
// the HLS unit's (the DLL's) values: ARX lanes exactly, Monolith lanes mod p (the datapaths may hold p or 0).
//   Vtop <trace>
// STIM=<file>: one line per clock phase from the reset on (every input, then lout after the phase's eval, vectors in hex
// MSB first): the stimulus and expected outputs of the gate-level replay (test/tb_gl.v, benchmark/power/power_vcd.sh).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include "verilated.h"
#include VTOP_H
typedef VTOP DUT;
static const uint32_t P = 0x7FFFFFFF;
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 2) { printf("usage: Vtop <trace>\n"); return 1; }
    std::ifstream f(argv[1]); std::string line;
    int nio = 0, ng = 0;
    std::getline(f, line); sscanf(line.c_str(), "H %d %d", &nio, &ng);
    DUT* dut = new DUT;
    const int NW = nio * 2;                                     // 32-bit words of the lane vectors
    std::vector<uint32_t> prev(NW, 0), lin(NW, 0);
    FILE* sf = getenv("STIM") ? fopen(getenv("STIM"), "w") : nullptr;
    const int NWI = (int)(sizeof(dut->lin) / sizeof(dut->lin[0]));
    auto hexv = [&](FILE* o, const uint32_t* w, int n) { fputc(' ', o); for (int i = n - 1; i >= 0; i--) fprintf(o, "%08x", w[i]); };
    auto ev = [&]() {
        dut->eval();
        if (!sf) return;
        fprintf(sf, "%d %d %d %d %d %d %x %x %llx", (int)dut->clk, (int)dut->rst, (int)dut->mono, (int)dut->mono2, (int)dut->htap,
                (int)dut->blake, (unsigned)dut->r, (unsigned)dut->r2, (unsigned long long)dut->rg);
        hexv(sf, (const uint32_t*)&dut->lin[0], NWI); hexv(sf, (const uint32_t*)&dut->lout[0], NWI); fputc(10, sf);
    };
    dut->clk = 0; dut->rst = 1; ev(); dut->clk = 1; ev(); dut->clk = 0; dut->rst = 0; ev();
    // the HLS unit starts from zero registers: run zero inputs through every pipeline first (18 cycles)
    for (int i = 0; i < 2 * 20 - 1; i++) { dut->clk = !dut->clk; ev(); }
    dut->clk = 0; ev();
    long cyc = 0, checks = 0, bad = 0, badcyc = 0, words = 0;
    bool have = false;
    auto apply_and_step = [&]() {
        for (int i = 0; i < NW; i++) dut->lin[i] = lin[i];
        ev();
        for (int i = 0; i < NW; i++) prev[i] = dut->lout[i];          // out of this call = prev of the next
        dut->clk = 1; ev();
        dut->clk = 0;
        cyc++;
    };
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        char k = line[0];
        if (k == 'T' || k == 'Z') {
            if (have) apply_and_step();
            if (k == 'Z') break;
            int mono, mono2, htap, blake, r, r2; unsigned long long rgv;
            sscanf(line.c_str(), "T %d %d %d %d %d %d %llx", &mono, &mono2, &htap, &blake, &r, &r2, &rgv);
            dut->mono = mono; dut->mono2 = mono2; dut->htap = htap; dut->blake = blake; dut->r = r; dut->r2 = r2;
            dut->rg = (decltype(dut->rg))rgv;
            std::fill(lin.begin(), lin.end(), 0); have = true;
        } else if (k == 'E') {                                        // expected values of a finishing node (from prev)
            std::istringstream ss(line.substr(2)); int lo, n, mode; ss >> lo >> n >> mode;
            int e = 0;
            for (int i = 0; i < n; i++) {
                std::string h; ss >> h; unsigned long long v = std::stoull(h, nullptr, 16);
                uint32_t elo = (uint32_t)v, ehi = (uint32_t)(v >> 32), glo = prev[2 * (lo + i)], ghi = prev[2 * (lo + i) + 1];
                if (mode == 1) { elo %= P; ehi %= P; glo %= P; ghi %= P; }
                if (elo != glo) e++;
                if (ehi != ghi) e++;
                words += 2;
                if ((elo != glo || ehi != ghi) && bad + e <= 6)
                    printf("cycle %ld lane %d: got %08x%08x expected %08x%08x (mode %d)\n", cyc, lo + i, ghi, glo, ehi, elo, mode);
            }
            checks++; bad += e; if (e) badcyc++;
        } else if (k == 'F') {                                        // fresh lanes
            std::istringstream ss(line.substr(2)); int lo; ss >> lo; std::string h; int i = 0;
            while (ss >> h) { unsigned long long v = std::stoull(h, nullptr, 16); lin[2 * (lo + i)] = (uint32_t)v; lin[2 * (lo + i) + 1] = (uint32_t)(v >> 32); i++; }
        } else if (k == 'P') {                                        // copies from the RTL's previous output
            int dlo, n, slo; sscanf(line.c_str(), "P %d %d %d", &dlo, &n, &slo);
            for (int i = 0; i < 2 * n; i++) lin[2 * dlo + i] = prev[2 * slo + i];
        }
    }
    if (sf) { dut->clk = 0; ev(); fclose(sf); }
    printf("SUMMARY: %s, %s: %ld cycles, %ld node finishes checked (%ld words), %ld mismatching words in %ld finishes\n",
           TOPNAME, argv[1], cyc, checks, words, bad, badcyc);
    delete dut; return bad ? 1 : 0;
}
