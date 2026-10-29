// tb_unit18.cpp - Verilator: a hand-written unit (RTL/unit18) runs a compiled program (compile_tree.py trace=) closed loop,
// cycle by cycle. Per cycle: the controls; the lanes the program writes fresh; the lanes it copies from the previous
// output (here: the RTL's own previous output); at every node finish the lanes the result is read from are compared with
// the HLS unit's (the DLL's) values: ARX lanes exactly, Monolith lanes mod p (the datapaths may hold p or 0).
//   Vtop <trace>
// Built with --trace (power.sh: the gate-level netlist): VCD=<file> VCD_FROM=<cycle> VCD_TO=<cycle> dump every signal in that
// window of program cycles (clock period 1000 ps, time 0 at VCD_FROM: OpenSTA read_vcd takes the VCD's end time over the
// number of clock edges as the period). VCD=<file> VCD_ALL=1 instead dumps from the reset on (time 0, 500 ps per clock phase),
// built with --trace-depth 1: the ports only, the stimulus that replays the program on the gate netlist (syn/power_vcd.sh).
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include "verilated.h"
#if VM_TRACE
#include "verilated_vcd_c.h"
#endif
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
#if VM_TRACE
    const char* vf = getenv("VCD");
    long vfrom = getenv("VCD_FROM") ? atol(getenv("VCD_FROM")) : 0, vto = getenv("VCD_TO") ? atol(getenv("VCD_TO")) : 0;
    const bool vall = getenv("VCD_ALL") != nullptr;
    uint64_t tall = 0;                                          // VCD_ALL: time of the next phase
    VerilatedVcdC* tfp = nullptr;
    if (vf) { Verilated::traceEverOn(true); tfp = new VerilatedVcdC; dut->trace(tfp, 99); tfp->set_time_unit("1ps"); tfp->set_time_resolution("1ps");
              if (vall) tfp->open(vf); }
    auto ev = [&]() { dut->eval(); if (vall && tfp) { tfp->dump(tall); tall += 500; } };
#else
    auto ev = [&]() { dut->eval(); };
#endif
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
#if VM_TRACE
        bool on = tfp && !vall && cyc >= vfrom && cyc < vto;
        if (on && !tfp->isOpen()) tfp->open(vf);
        if (on) tfp->dump((uint64_t)(cyc - vfrom) * 1000);                       // clock low, inputs of this cycle applied
#endif
        dut->clk = 1; ev();
#if VM_TRACE
        if (on) tfp->dump((uint64_t)(cyc - vfrom) * 1000 + 500);                 // after the rising edge
#endif
        dut->clk = 0;
        cyc++;
#if VM_TRACE
        if (tfp && !vall && tfp->isOpen() && cyc == vto) { tfp->dump((uint64_t)(cyc - vfrom) * 1000); tfp->close(); }
#endif
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
#if VM_TRACE
    if (vall && tfp) { dut->clk = 0; ev(); tfp->close(); }
#endif
    printf("SUMMARY: %s, %s: %ld cycles, %ld node finishes checked (%ld words), %ld mismatching words in %ld finishes\n",
           TOPNAME, argv[1], cyc, checks, words, bad, badcyc);
    delete dut; return bad ? 1 : 0;
}
