#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Interface to the /proc/interrupts file.

"""

FILE="/proc/interrupts"

class _CPU(object):
    def __init__(self, cpu, count=0):
        self.cpu = int(cpu)
        self.count = int(count)
    def __str__(self):
        return "CPU%d: IRQ count = %u" % (self.cpu, self.count)


class _InterruptLine(object):
    def __init__(self):
        self.name = None
        self.handlername = None
        self.actions = None
        self._cpus = []

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        #  5:       3306          XT-PIC  Ensoniq AudioPCI
        cs = "".join(["%10u " % (c.count,) for c in self._cpus])
        return "%-3s: %s %14s  %s" % (self.name, cs, self.handlername, self.actions)

#  15:    1539950          XT-PIC  aic7xxx, usb-uhci
    def update(self, line, cpus):
        self._cpus = []
        name, line = line.split(":", 1)
        try:
            self.name = int(name)
        except ValueError:
            self.name = name

        for cpu in cpus:
            newcpu = _CPU(cpu.cpu)
            try:
                cs, line = line.split(None, 1)
            except ValueError:
                newcpu.count = int(line)
                line = None
            else:
                newcpu.count = int(cs)
            self._cpus.append(newcpu)
        if line:
            self.handlername, line = line.split(None, 1)
            self.actions = line.strip()

    def __getitem__(self, idx):
        return self._cpus[idx]


class Interrupts(object):
    def __init__(self):
        self._cpus = []
        self._err = 0 # IRQ Error count
        self._mis = 0 # APIC mismatch count

    def update(self):
        self._cpus = []
        self._irqs = {}
        lines = open(FILE).readlines()
        for rcpu in lines[0].split():
            idx = int(rcpu[3:])
            self._cpus.append(_CPU(idx))

        for line in lines[1:]:
            if line.startswith("ERR"):
                self._err = int(line.split(":")[1])
            elif line.startswith("MIS"):
                self._mis = int(line.split(":")[1])
            else:
                irq = _InterruptLine()
                irq.update(line, self._cpus)
                self._irqs[irq.name] = irq

    def __str__(self):
        # CPU header line
        h = ["           "]
        h.extend(["CPU%d       " % (c.cpu,) for c in self._cpus])
        s = ["".join(h)]

        s.extend(list(map(str, list(self._irqs.values()))))

        s.append("ERR: %10u" % (self._err,))
        s.append("MIS: %10u" % (self._mis,))
        return "\n".join(s)

    def __getitem__(self, idx):
        return self._irqs[idx]


def get_interrupts():
    ir = Interrupts()
    ir.update()
    return ir

def _test(argv):
    ir = get_interrupts()
    print(ir)
    print(ir[5][0]) # index by IRQ, CPU

if __name__ == "__main__":
    import sys
    _test(sys.argv)

