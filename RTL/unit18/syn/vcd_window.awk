# vcd_window.awk - cut the window [T0, T1] out of a VCD stream (fst2vcd output), times rebased to 0: the header, then at #0 a
# $dumpvars with every signal's value at T0 (the last change before it), then the changes inside the window.
#   fst2vcd x.fst | awk -v T0=<t> -v T1=<t> -f vcd_window.awk > window.vcd
BEGIN { hdr = 1; t = -1; on = 0 }
hdr { print; if ($1 == "$enddefinitions") hdr = 0; next }
/^#/ {
    t = substr($1, 2) + 0
    if (!on && t >= T0) {
        on = 1; print "#0"; print "$dumpvars"
        for (k in last) print last[k]
        print "$end"
    }
    if (on && t > T1) { print "#" (T1 - T0); exit }
    if (on && t > T0) print "#" (t - T0)
    next
}
/^\$/ { next }                                              # $dumpvars / $end / $comment of the source
{
    if (substr($0, 1, 1) == "b" || substr($0, 1, 1) == "r") id = $2; else id = substr($0, 2)
    if (on) print; else last[id] = $0
}
