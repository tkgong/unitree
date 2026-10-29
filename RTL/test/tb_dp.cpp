// tb_dp.cpp - Verilator: mono_dp18 alone against the Python model's vectors (test/dp_vec.py): every line
// "r x0..x15 y0..y15" (hex) is one traversal of one state; the datapath output 18 cycles later is compared mod p.
//   Vmono_dp18 <vectors>
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include "verilated.h"
#include "Vmono_dp18.h"
static const uint32_t P = 0x7FFFFFFF;
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::ifstream f(argv[1]); std::string line;
    std::vector<std::vector<uint32_t>> vec;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        std::istringstream ss(line); std::vector<uint32_t> v; std::string h;
        while (ss >> h) v.push_back((uint32_t)std::stoul(h, nullptr, 16));
        if (v.size() == 33) vec.push_back(v);
    }
    Vmono_dp18* dut = new Vmono_dp18;
    dut->clk = 0; dut->rst = 1; dut->mono = 0; dut->r = 0;
    for (int i = 0; i < 16; i++) dut->x[i] = 0;
    dut->ea = 0; dut->eb = 0;                                    // NL = 0: one 32-bit word each
    dut->eval(); dut->clk = 1; dut->eval(); dut->clk = 0; dut->rst = 0; dut->eval();
    long bad = 0, n = (long)vec.size();
    for (long c = 0; c < n + 18; c++) {
        if (c < n) {
            dut->mono = 1; dut->r = vec[c][0];
            for (int k = 0; k < 8; k++) { dut->x[2 * k] = vec[c][1 + 2 * k]; dut->x[2 * k + 1] = vec[c][1 + 2 * k + 1]; }
        } else { dut->mono = 0; dut->r = 0; for (int i = 0; i < 16; i++) dut->x[i] = 0; }
        dut->eval();
        if (c >= 18) {
            long t = c - 18; int e = 0;
            for (int i = 0; i < 16; i++) {
                uint32_t got = dut->y[i] % P, exp = vec[t][17 + i] % P;
                if (got != exp) { e++; if (bad < 8) printf("vector %ld r=%u elem %d: got %08x expected %08x\n", t, vec[t][0], i, dut->y[i], vec[t][17 + i]); }
            }
            if (e) bad++;
        }
        dut->clk = 1; dut->eval(); dut->clk = 0; dut->eval();
    }
    printf("SUMMARY: mono_dp18, %ld vectors, %ld bad\n", n, bad);
    delete dut; return bad ? 1 : 0;
}
