"""Aplica cada defeito candidato numa cópia e confere se as referências falham.

Uso dentro da imagem: python defeitos_candidatos.py /defeitos/candidatos.json
Exige ocorrência única do trecho. Sai com código 1 se algum defeito sobreviver.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

RAIZES = {"fava": "src", "bump-my-version": ".", "python-dotenv": "src", "python-stdnum": "."}
defeitos = json.loads(Path(sys.argv[1]).read_text())
falhas = 0
for d in defeitos:
    origem = Path("/projetos") / d["projeto"]
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / d["projeto"]
        shutil.copytree(origem, copia, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        alvo = copia / d["path"]
        texto = alvo.read_text()
        n = texto.count(d["old"])
        if n != 1:
            print(f"ERRO  {d['id']}: trecho aparece {n} vezes"); falhas += 1; continue
        alvo.write_text(texto.replace(d["old"], d["new"]))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                            "--import-mode=importlib", "tcc_referencia"], cwd=copia, capture_output=True, text=True,
                           env={"PYTHONPATH": str(copia / RAIZES[d["projeto"]]), "PYTHONDONTWRITEBYTECODE": "1",
                                "PATH": "/usr/local/bin:/usr/bin:/bin"})
        resumo = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-200:]
        falhou = [l.split(" - ")[0].replace("FAILED ", "") for l in r.stdout.splitlines() if l.startswith("FAILED")]
        if r.returncode == 1 and falhou:
            print(f"ok    {d['id']:34} detectado por {len(falhou)}: {', '.join(f.split('::')[-1] for f in falhou[:3])}")
        else:
            print(f"VIVO  {d['id']:34} {resumo}"); falhas += 1
sys.exit(1 if falhas else 0)
