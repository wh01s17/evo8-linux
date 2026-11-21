// Dump the vtables of UacLib / Evo model classes and the callers of each slot.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.*;
import java.io.PrintWriter;

public class DumpUacVtables extends GhidraScript {
    @Override
    public void run() throws Exception {
        PrintWriter out = new PrintWriter(getScriptArgs()[0]);
        SymbolTable st = currentProgram.getSymbolTable();
        SymbolIterator it = st.getSymbols("vftable");
        while (it.hasNext()) {
            Symbol s = it.next();
            String ns = s.getParentNamespace().getName(true);
            if (!(ns.contains("UacXU") || ns.contains("UacMixerUnit") || ns.contains("UacExtensionUnit")
                  || ns.contains("UacXUBase") || ns.endsWith("Model") || ns.contains("UacFeatureUnit"))) continue;
            out.println("== " + ns + " @ " + s.getAddress());
            Address a = s.getAddress();
            for (int i = 0; i < 40; i++) {
                Address slot = a.add(i * 4);
                int v = getInt(slot);
                Address target = toAddr(v & 0xffffffffL);
                Function f = getFunctionAt(target);
                if (f == null) break;
                out.println(String.format("  [%2d] %s %s", i, target, f.getName()));
            }
        }
        // Callers of the XU request wrappers.
        String[] wrappers = {"006589e0","00658ab0","00658a40","00658b80","00658b10","00658b40","00658ae0","00658bb0",
            "00658c80","00658cb0","00658c20","00658c50","00658e10","00658d00","00658d30","00658ed0","00658f10","00658e40",
            "00658d60","00658e70","00658ea0","00658a70","00658bf0","00658550","006587f0","00658ce0"};
        for (String w : wrappers) {
            Address a = toAddr(w);
            out.print("callers " + w + ":");
            for (Reference r : getReferencesTo(a)) {
                Function f = getFunctionContaining(r.getFromAddress());
                out.print(" " + r.getFromAddress() + (f != null ? "(" + f.getName() + ")" : "") + "/" + r.getReferenceType());
            }
            out.println();
        }
        out.close();
    }
}
