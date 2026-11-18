#include <cstdint>
#include <string>
#include <sstream>
#include <vector>
#include <deque>
#include <unordered_map>

#include "base/base.h"
#include "base/config.h"
#include "base/request.h"
#include "frontend/frontend.h"
#include "memory_system/memory_system.h"
#include "dram/dram.h"
#include "dram_controller/controller.h"
#include "dram_controller/plugin.h"

namespace {
struct Sim {
  Ramulator::IFrontEnd* fe = nullptr;
  Ramulator::IMemorySystem* ms = nullptr;
  Ramulator::IDRAM* dram = nullptr;
  std::deque<uint64_t> done;
  std::vector<uint64_t> cmd;
};
Sim* g_creating = nullptr;
}

namespace Ramulator {
class UnitreeCmdCount : public IControllerPlugin, public Implementation {
  RAMULATOR_REGISTER_IMPLEMENTATION(IControllerPlugin, UnitreeCmdCount, "UnitreeCmdCount", "Counts issued DRAM commands (unitree co-simulation).")
 private:
  Sim* m_sim = nullptr;
 public:
  void init() override {}
  void setup(IFrontEnd* frontend, IMemorySystem* memory_system) override {
    m_ctrl = cast_parent<IDRAMController>();
    m_sim = g_creating;
  }
  void update(bool request_found, ReqBuffer::iterator& req_it) override {
    if (!request_found || m_sim == nullptr) return;
    size_t c = (size_t)req_it->command;
    if (c >= m_sim->cmd.size()) m_sim->cmd.resize(c + 1, 0);
    m_sim->cmd[c]++;
  }
};
}

extern "C" {

void* hbm_new(const char* yaml, const char* overrides) {
  std::vector<std::string> params;
  std::stringstream ss(overrides ? overrides : "");
  for (std::string line; std::getline(ss, line);)
    if (!line.empty()) params.push_back(line);
  YAML::Node config = Ramulator::Config::parse_config_file(yaml, params);
  Sim* s = new Sim();
  g_creating = s;
  s->fe = Ramulator::Factory::create_frontend(config);
  s->ms = Ramulator::Factory::create_memory_system(config);
  s->fe->connect_memory_system(s->ms);
  s->ms->connect_frontend(s->fe);
  s->dram = s->ms->get_ifce<Ramulator::IDRAM>();
  g_creating = nullptr;
  return s;
}

int hbm_send(void* h, uint64_t addr, int is_write, uint64_t tag) {
  Sim* s = (Sim*)h;
  int type = is_write ? Ramulator::Request::Type::Write : Ramulator::Request::Type::Read;
  Ramulator::Request req((Ramulator::Addr_t)addr, type, 0, [s, tag](Ramulator::Request&) { s->done.push_back(tag); });
  return s->ms->send(req) ? 1 : 0;
}

int hbm_tick(void* h, uint64_t* out, int max) {
  Sim* s = (Sim*)h;
  s->ms->tick();
  int n = 0;
  while (n < max && !s->done.empty()) { out[n++] = s->done.front(); s->done.pop_front(); }
  return n;
}

uint64_t hbm_cmd(void* h, const char* name) {
  Sim* s = (Sim*)h;
  if (!s->dram->m_commands.contains(name)) return (uint64_t)-1;
  size_t c = (size_t)s->dram->m_commands(name);
  return c < s->cmd.size() ? s->cmd[c] : 0;
}

int hbm_level(void* h, const char* level) {
  Sim* s = (Sim*)h;
  return s->dram->get_level_size(level);
}

double hbm_tck_ns(void* h) { return ((Sim*)h)->ms->get_tCK(); }

void hbm_free(void* h) { delete (Sim*)h; }

}
