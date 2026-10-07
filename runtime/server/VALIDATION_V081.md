# v0.8.1 validation / ստուգումներ

CONFIRMED HERE: Python3.12.14 Linux unittest69OK. New success/failure-path tests explicitly try SELECT on every backup snapshot connection and require ProgrammingError (closed). Removing contextlib.closing via an in-memory test patch makes both new tests fail on Linux; no working files were reverted. Recovery-preservation test additionally requires its snapshot connection closed. JS4/10/6/10+11PASS; source site59/59SHA256 unchanged.

CLAUDE-REPORTED: v0.8.0 VPS67OK, JS pass, STAGING installed and repeated planner stable; Windows has two WinError32 errors in backup/test snapshot cleanup. Existing runtime/recovery explicitly close connections; all three remaining with-sqlite-connect usages were corrected.

UNVERIFIED: actual Windows and VPS v0.8.1 acceptance, authenticated browser checks for new outer Nginx gate, correct-password access from a different network (phase5 IP removal/unauthenticated401 checks reported by Claude). No deployment, message or live attachment was performed here. No connection/source/credential was available for direct VPS work.

HY: Տեղում69թեստը անցել է, փակվելու թեստերը հին վարքի դեպքում ձախողվում են նաև Linux-ում։ Windows/VPS նոր անցումը դեռ չի ստուգվել։ Փուլ5-ի փոխանցմամբ IP կանոնը հանված է․ պահպանել գործող Basic փակումը և ստուգել ճիշտ գաղտնաբառով մյուս ցանցի մուտքն ու capture-ը։
