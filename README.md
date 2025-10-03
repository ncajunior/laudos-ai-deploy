# Laudos AI

Projeto: geração automatizada de laudos de vistoria e avaliação de imóveis municipais.

Resumo
------
Este repositório contém um serviço FastAPI que gera PDFs de laudos técnicos automatizados com auxílio do OpenAI para produzir as descrições técnicas. O serviço também gera um hash SHA256 do PDF, cria um QR code apontando para um endpoint de verificação e concatena uma página de assinatura simples.

Arquitetura
----------
- `laudos-api` (FastAPI): API para gerar laudos e endpoints auxiliares.
- `nginx`: proxy reverso e servidor estático para os PDFs gerados.
- `./laudos`: volume onde os PDFs gerados são armazenados.
- `api/scripts/gerar_laudo.py`: gerador do PDF (ReportLab + OpenAI + PyPDF2 + qrcode)

Como rodar (desenvolvimento)
----------------------------
1. Copie `.env.example` para `.env` e edite as variáveis necessárias:

   - `OPENAI_API_KEY`: sua chave OpenAI (dev)
   - `LAUDOS_DIR` (opcional): diretório de saída dentro do container
   - `IMAGENS_DIR` (opcional): diretório onde imagens são buscadas

2. Inicie containers:

```bash
docker-compose up -d --build
```

3. Verifique health:

```bash
curl http://localhost/health
```

4. Gerar um laudo de teste:

```bash
curl -X POST http://localhost:8000/api/gerar_laudo/12345 -H 'Content-Type: application/json' -d '{}'
```

Arquivos importantes
-------------------
- `api/main.py`: FastAPI app com endpoints:
  - `GET /health` — status
  - `POST /api/gerar_laudo/{tombamento}` — gera e retorna caminho do PDF
  - `GET /verificar?hash=<sha256>` — verifica laudo por hash
  - `POST /api/atualiza_centroid` — atualiza centroid de um imóvel (usa `DATABASE_URL`)
  - `POST /api/rollback` — atualmente desabilitado por segurança (retorna 403)
- `api/scripts/gerar_laudo.py`: lógica de geração de PDF, integração com OpenAI, inserção de foto, geração de hash e QR, concatenação do PDF assinado
- `nginx.conf`: configuração do proxy e servidor estático para `/laudos/`
- `docker-compose.yml`: orquestra serviços `laudos-api` e `nginx`

Variáveis de ambiente
---------------------
- `OPENAI_API_KEY` (obrigatório para usar geração via OpenAI)
- `DATABASE_URL` (opcional) — string de conexão para Postgres/PostGIS
- `LAUDOS_DIR` (opcional) — diretório dentro do container para saída de PDFs (padrão `/app/laudos`)
- `IMAGENS_DIR` (opcional) — diretório dentro do container para imagens usadas nos laudos

Segurança e recomendações
------------------------
- NÃO comite `.env` com chaves. `/.gitignore` já contém `.env`.
- Se uma chave foi exposta, revogue-a e gere uma nova no painel da OpenAI.
- Para produção, use um secret manager (Vault, AWS Secrets Manager, GitHub Actions secrets).
- A rota `POST /api/rollback` foi desabilitada. Rollbacks e deploys devem ser feitos via CI/CD ou SSH seguro.

Deploy e rollback seguro
------------------------
Siga estas práticas para deploy e rollback seguros — NÃO use endpoints HTTP para executar comandos de deploy/rollback.

1) Deploy via CI/CD (recomendado)
   - Use GitHub Actions (ou seu CI) para buildar a imagem, rodar testes e publicar artefatos.
   - No `deploy` job, conecte-se ao servidor de destino por SSH (com chave privada armazenada em GitHub Secrets) e execute o `docker-compose pull && docker-compose up -d --remove-orphans` ou uma rotina de rolling update.
   - Exemplo simplificado do passo de deploy (GitHub Actions):

```yaml
# trecho para inserir em .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Set up SSH
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
      - name: Deploy to server
        run: |
          ssh -o StrictHostKeyChecking=no ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            'cd /opt/laudos && git pull origin main && docker-compose pull && docker-compose up -d --remove-orphans'
```

2) Rollback seguro
   - Use tags/releases e um job de rollback controlado pelo CI (não por HTTP).
   - Para reverter, escolha um commit seguro (tag) e execute no servidor:

```bash
ssh deploy@server 'cd /opt/laudos && git fetch --tags && git checkout <tag_or_commit_sha> && docker-compose pull && docker-compose up -d --remove-orphans'
```

3) Boas práticas adicionais
   - Proteja branches principais (branch protection rules) e force PRs com revisão antes de merge.
   - Use healthchecks e readiness probes para validar deploys antes de trocar tráfego.
   - Mantenha backups e versionamento de configurações (ex.: configuração do nginx, docker-compose).


O que falta (próximos passos)
----------------------------
- Implementar validações PostGIS (centroid, shapes, consistência) e armazenar logs de inconsistências.
- Implementar tratamento automático com AGNO (fila, cards, revisão humana).
- Gerar mapas no PDF (geopandas/matplotlib/QGIS/MapFish).
- Implementar cálculo de avaliação (valores por setor) e inclusão no PDF.
- Assinatura digital legal (PAdES) para validade jurídica.
- Tests unitários e CI pipeline (GitHub Actions).

Contribuição
------------
Crie branches de feature e abra PRs contra `main`.

Licença
-------
Repositório sob licença permissiva — adicione a licença desejada se necessário.
