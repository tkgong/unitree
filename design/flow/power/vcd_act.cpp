#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <iostream>
struct Var { std::string name; int w, msb, lsb; std::string val; uint64_t tlast; std::vector<uint32_t> tog; std::vector<uint64_t> hi; };
int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: vcd_act <vcd>\n"); return 1; }
    std::ifstream in(argv[1]); std::string line;
    std::vector<Var> vars; std::unordered_map<std::string, std::vector<int>> byid;
    std::vector<std::string> scope;
    bool hdr = true, on = false; uint64_t t = 0, t0 = 0;
    auto setv = [&](Var& v, const std::string& nv) {
        uint64_t dt = t - v.tlast;
        for (int i = 0; i < v.w; i++) {
            char a = v.val[i], b = nv[i];
            if (a == '1') v.hi[i] += dt;
            if ((a == '1') != (b == '1') && (a == '0' || a == '1') && (b == '0' || b == '1')) v.tog[i]++;
        }
        v.val = nv; v.tlast = t;
    };
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        if (hdr) {
            if (line.find("$enddefinitions") != std::string::npos) { hdr = false; continue; }
            if (line.find("$var") != std::string::npos) {
                char ty[32], id[64], nm[4096], rg[64]; int w = 0; rg[0] = 0;
                int k = sscanf(line.c_str(), " $var %31s %d %63s %4095s %63s", ty, &w, id, nm, rg);
                if (k < 4) continue;
                Var v; v.name = nm; v.w = w; v.msb = w - 1; v.lsb = 0;
                if (rg[0] == '[') { int a, b; if (sscanf(rg, "[%d:%d]", &a, &b) == 2) { v.msb = a; v.lsb = b; } else if (sscanf(rg, "[%d]", &a) == 1) { v.msb = v.lsb = a; } }
                v.val.assign(w, 'x'); v.tlast = 0; v.tog.assign(w, 0); v.hi.assign(w, 0);
                byid[id].push_back((int)vars.size()); vars.push_back(v);
            }
            continue;
        }
        char c = line[0];
        if (c == '#') {
            t = strtoull(line.c_str() + 1, nullptr, 10);
            continue;
        }
        if (c == '$') {
            if (line.compare(0, 8, "$dumpon") == 0 || line.compare(0, 7, "$dumpon") == 0) {
                if (!on) { on = true; t0 = t; for (auto& v : vars) { v.tlast = t; v.val.assign(v.w, 'x'); } }
            } else if (line.compare(0, 8, "$dumpoff") == 0 && on) break;
            continue;
        }
        if (!on) continue;
        std::string id, val;
        if (c == 'b' || c == 'B') { size_t sp = line.find(' '); val = line.substr(1, sp - 1); id = line.substr(sp + 1); }
        else if (c == 'r' || c == 'R') continue;
        else { val = std::string(1, c); id = line.substr(1); }
        auto it = byid.find(id); if (it == byid.end()) continue;
        for (int vi : it->second) {
            Var& v = vars[vi];
            std::string nv = val;
            if ((int)nv.size() < v.w) { char pad = (nv[0] == 'x' || nv[0] == 'z') ? nv[0] : '0'; nv = std::string(v.w - nv.size(), pad) + nv; }
            else if ((int)nv.size() > v.w) nv = nv.substr(nv.size() - v.w);
            setv(v, nv);
        }
    }
    printf("SPAN %llu\n", (unsigned long long)(t - t0));
    for (auto& v : vars) {
        setv(v, v.val);
        for (int i = 0; i < v.w; i++) {
            int bit = (v.msb >= v.lsb) ? v.msb - i : v.msb + i;
            if (v.w == 1 && v.msb == v.lsb && v.msb == 0) printf("%s %u %llu\n", v.name.c_str(), v.tog[i], (unsigned long long)v.hi[i]);
            else printf("%s[%d] %u %llu\n", v.name.c_str(), bit, v.tog[i], (unsigned long long)v.hi[i]);
        }
    }
    return 0;
}
