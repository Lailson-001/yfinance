"""Envia os Parquets processados para um bucket S3."""

import argparse
import os
import sys
from collections.abc import Sequence

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import BotoCoreError, ClientError

from .environment import get_project_paths


def main(argv: Sequence[str] | None = None) -> int:
    """Lê o destino da CLI e publica os Parquets com boto3."""
    parser = argparse.ArgumentParser(
        prog="b3-upload",
        description="Envia os arquivos Parquet de data/processed para o S3.",
    )
    parser.add_argument("--bucket", required=True, metavar="NOME", help="nome do bucket S3")
    parser.add_argument(
        "--prefix", "--folder", default="", metavar="PASTA",
        help="prefixo no bucket, por exemplo b3/processados (padrão: raiz do bucket)",
    )
    args = parser.parse_args(argv)

    access_key = os.environ.get("aws_key")
    secret_key = os.environ.get("aws_secret_key")
    if not access_key or not secret_key:
        print("Defina as variáveis de ambiente aws_key e aws_secret_key.", file=sys.stderr)
        return 2

    processed_dir = get_project_paths().processed
    files = sorted(path for path in processed_dir.glob("*.parquet") if path.is_file())
    if not files:
        print(f"Nenhum arquivo Parquet encontrado em {processed_dir}.", file=sys.stderr)
        return 1

    try:
        s3 = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    except (BotoCoreError, ClientError) as exc:
        print(f"Erro ao configurar o cliente S3: {exc}", file=sys.stderr)
        return 1

    prefix = args.prefix.strip("/")
    uploaded = 0
    for path in files:
        key = f"{prefix}/{path.name}" if prefix else path.name
        destination = f"s3://{args.bucket}/{key}"
        try:
            s3.upload_file(str(path), args.bucket, key)
        except (S3UploadFailedError, BotoCoreError, ClientError, OSError) as exc:
            print(f"Falha ao enviar para {destination}: {exc}", file=sys.stderr)
            continue
        uploaded += 1
        print(f"Enviado: {destination}")

    print(f"Arquivos enviados: {uploaded}/{len(files)}.")
    return 0 if uploaded == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
