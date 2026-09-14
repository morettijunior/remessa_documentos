from pathlib import Path


def verificar_arquivos_pedido(dados_pedido, caminhos_config):
    """Valida e retorna os caminhos reais dos arquivos no disco com base nas regras."""
    arquivos_encontrados = {
        "PEDIDO": None,
        "NFS_PDF": None,
        "NFE_PDF": None,
        "NFE_XML": None,
        "BOLETOS": [],
    }

    # 1. Caminho do PDF do Pedido (Ex: C:\TGA\32309.pdf)
    numero_pedido = dados_pedido.get("NUMERO_PEDIDO")
    if numero_pedido:
        caminho_pedido = (
            Path(caminhos_config["DIR_PDF_PEDIDO"])
            / f"{numero_pedido}.pdf"
        )
        if caminho_pedido.exists():
            arquivos_encontrados["PEDIDO"] = str(caminho_pedido)

    # 2. Caminho da NFS PDF (Ex: \\Servidor\tga\NFS-e\XML\18879-nfse.pdf)
    numero_nfs = dados_pedido.get("NFS")
    if numero_nfs:
        caminho_nfs = (
            Path(caminhos_config["DIR_NFS_PDF"])
            / f"{numero_nfs}-nfse.pdf"
        )
        if caminho_nfs.exists():
            arquivos_encontrados["NFS_PDF"] = str(caminho_nfs)

    # 3. Caminho da NFe PDF e XML (Usa a Chave de Acesso e a pasta AnoMês, ex: 202609)
    chave = dados_pedido.get("CHAVEACESSO_NFE")
    ano_mes = dados_pedido.get("ANO_MES_NFE")

    if chave and ano_mes:
        # NFe PDF: DIR_NFE_PDF \ AnoMes \ ChaveAcesso-nfe.pdf
        caminho_nfe_pdf = (
            Path(caminhos_config["DIR_NFE_PDF"]) / ano_mes / f"{chave}-nfe.pdf"
        )
        if caminho_nfe_pdf.exists():
            arquivos_encontrados["NFE_PDF"] = str(caminho_nfe_pdf)

        # NFe XML: DIR_NFE_XML \ AnoMes \ NFe \ ChaveAcesso-nfe.xml
        caminho_nfe_xml = (
            Path(caminhos_config["DIR_NFE_XML"]) / ano_mes / "NFe" / f"{chave}-nfe.xml"
        )
        if caminho_nfe_xml.exists():
            arquivos_encontrados["NFE_XML"] = str(caminho_nfe_xml)

    return arquivos_encontrados