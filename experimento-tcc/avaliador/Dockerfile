# Imagem única do avaliador para as 108 gerações do TCC.
# Instala as dependências dos quatro projetos com versões exatas
# (requirements.lock.txt, gerado em 21/11/2026 a partir de fava 1.30.16,
# bump-my-version 1.8.1, python-dotenv 1.2.4 e python-stdnum 2.2).
# Os próprios projetos não são instalados: o código avaliado vem das pastas em
# ../projetos, nas revisões fixadas, pelo PYTHONPATH que o ContextLab monta.
# Exceção: python-dotenv fica instalado por ser dependência do pydantic-settings,
# usado pelo bump-my-version; no projeto python-dotenv, o PYTHONPATH tem precedência.
# A avaliação roda sem rede.
FROM python:3.12.11-slim
COPY requirements.lock.txt /opt/requirements.lock.txt
RUN python -m pip install --no-cache-dir --no-deps -r /opt/requirements.lock.txt \
 && python -m pip check
WORKDIR /project
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
