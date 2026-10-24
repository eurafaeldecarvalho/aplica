# engine/ — vendorado
Cópia do motor do plugin [aplica](https://github.com/eurafaeldecarvalho/aplica), empacotada no app
para leituras locais do banco (`jobdb.py`). As execuções agênticas usam o plugin via `claude -p`.
Mantenha em sincronia; `jobdb.py check` avisa se o `schema_version` do banco divergir do motor.
