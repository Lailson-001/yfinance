# B3 Pipeline

## Enviar os Parquets ao Amazon S3

Use um bucket existente e credenciais com permissão `s3:PutObject` no destino. No Bash, informe as credenciais quando o terminal pedir. Os valores digitados ficam ocultos.

```bash
read -rsp 'Chave de acesso AWS: ' aws_key; printf '\n'
read -rsp 'Chave secreta AWS: ' aws_secret_key; printf '\n'
export aws_key aws_secret_key

uv run b3-upload --bucket meu-bucket --prefix b3/processados
```

O comando envia os arquivos `.parquet` diretamente em `data/processed/` e preserva seus nomes. Por exemplo, `PETR4_SA.parquet` vai para `s3://meu-bucket/b3/processados/PETR4_SA.parquet`. Você pode usar `--folder` no lugar de `--prefix`. Ao omitir o prefixo, os arquivos vão para a raiz do bucket.

Um novo envio para a mesma chave atualiza o objeto. Buckets com versionamento habilitado preservam as versões anteriores.
