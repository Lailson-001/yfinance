# B3 Pipeline

## Enviar os Parquets ao Amazon S3

Use um bucket existente e credenciais com permissão `s3:PutObject` no destino. Crie um arquivo `.env` na raiz do projeto e substitua os valores de exemplo pelas suas credenciais.

```dotenv
aws_key=sua_chave_de_acesso
aws_secret_key=sua_chave_secreta
```

O comando lê o par de credenciais do `.env` automaticamente. Se o arquivo estiver ausente ou não declarar nenhuma das duas chaves, o comando usa as variáveis de ambiente do terminal.

```bash
uv run b3-upload --bucket meu-bucket --prefix b3/processados
```

O comando envia os arquivos `.parquet` diretamente em `data/processed/` e preserva seus nomes. Por exemplo, `PETR4_SA.parquet` vai para `s3://meu-bucket/b3/processados/PETR4_SA.parquet`. Você pode usar `--folder` no lugar de `--prefix`. Ao omitir o prefixo, os arquivos vão para a raiz do bucket.

Um novo envio para a mesma chave atualiza o objeto. Buckets com versionamento habilitado preservam as versões anteriores.
