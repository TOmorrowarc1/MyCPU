from assassyn.frontend import *

valid_CSRs=[
  Bits(12)(0x300),  # mstatus
  Bits(12)(0x301),  # misa
  Bits(12)(0x304),  # mie
  Bits(12)(0x344),  # mip
  Bits(12)(0x305),  # mtvec
  Bits(12)(0x341),  # mepc
  Bits(12)(0x342),  # mcause
  Bits(12)(0x343),  # mtval
  Bits(12)(0x340),  # mtscratch
  Bits(12)(0xF11),  # mvendorid
  Bits(12)(0xF12),  # marchid
  Bits(12)(0xF13),  # mimpid
  Bits(12)(0xF14),  # mhartid
  Bits(12)(0xF15),  # mconfigptr
  Bits(12)(0x302),  # medeleg
  Bits(12)(0x303),  # mideleg
  Bits(12)(0x306),  # mcounteren
  Bits(12)(0x310),  # mstatush
  Bits(12)(0x312),  # medelegh
  Bits(12)(0x34A),  # mtinst
  Bits(12)(0x34B),  # mtval2
]