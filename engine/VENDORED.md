# engine/ — vendorado

Esta pasta é uma **cópia** do motor do plugin [aplica](https://github.com/eurafaeldecarvalho/aplica),
empacotada no app para leituras locais do banco (`jobdb.py`) sem depender do plugin instalado.
As execuções agênticas de verdade usam o plugin via `claude -p`.

**Mantenha em sincronia com o repo do plugin.** `jobdb.py` carimba `schema_version` no `state.db`
no `init` e `jobdb.py check` avisa se o banco foi criado por uma versão diferente do motor.
