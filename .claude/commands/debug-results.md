Diagnose unexpected experimental results.

Steps:
1. Ask: what metric, what value, what was expected?
2. Check for: data leakage (temporal split violated?), label noise,
   class imbalance not handled, feature scaling issue, wrong evaluation split
3. Propose 2-3 targeted diagnostic experiments to isolate the cause
4. Do not suggest re-running everything - isolate first
