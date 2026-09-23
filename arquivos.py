from pathlib import Path

def verificar_arquivos_pedido(dados_pedido, caminhos_config):
    """Valida e retorna os caminhos reais dos arquivos no disco com base nas regras, aceitando variações de extensão."""
    arquivos_encontrados = {
        "PEDIDO": None,
        "NFS_PDF": None,
        "NFE_PDF": None,
        "NFE_XML": None,
        "BOLETOS": [],
    }

    # 1. Caminho do PDF do Pedido (Tratamento flexível para aceitar DIR_PDF_PEDIDO ou DIR_PEDIDO)
    dir_pedido = (
        caminhos_config.get("DIR_PDF_PEDIDO") 
        or caminhos_config.get("DIR_PEDIDO") 
        or ""
    )
    
    numero_pedido = str(dados_pedido.get("NUMERO_PEDIDO", "")).strip()
    if numero_pedido and dir_pedido:
        pasta_p = Path(dir_pedido)
        # Tenta variações de extensão (.pdf, .PDF) e busca case-insensitive opcional
        caminho_pedido = pasta_p / f"{numero_pedido}.pdf"
        if not caminho_pedido.exists():
            caminho_pedido_alt = pasta_p / f"{numero_pedido}.PDF"
            if caminho_pedido_alt.exists():
                caminho_pedido = caminho_pedido_alt

        if caminho_pedido.exists():
            arquivos_encontrados["PEDIDO"] = str(caminho_pedido)

    # 2. Caminho da NFS PDF (Ex: \\Servidor\tga\NFS-e\XML\18879-nfse.pdf)
    dir_nfs = caminhos_config.get("DIR_NFS_PDF")
    numero_nfs = str(dados_pedido.get("NFS", "")).strip()
    if numero_nfs and dir_nfs:
        pasta_nfs = Path(dir_nfs)
        caminho_nfs = pasta_nfs / f"{numero_nfs}-nfse.pdf"
        if not caminho_nfs.exists():
            caminho_nfs_alt = pasta_nfs / f"{numero_nfs}-nfse.PDF"
            if caminho_nfs_alt.exists():
                caminho_nfs = caminho_nfs_alt

        if caminho_nfs.exists():
            arquivos_encontrados["NFS_PDF"] = str(caminho_nfs)

    # 3. Caminho da NFe PDF e XML (Usa a Chave de Acesso e a pasta AnoMês, ex: 202609)
    chave = str(dados_pedido.get("CHAVEACESSO_NFE", "")).strip()
    ano_mes = str(dados_pedido.get("ANO_MES_NFE", "")).strip()

    if chave and ano_mes:
        # NFe PDF: DIR_NFE_PDF \ AnoMes \ ChaveAcesso-nfe.pdf
        dir_nfe_pdf = caminhos_config.get("DIR_NFE_PDF")
        if dir_nfe_pdf:
            pasta_nfe_pdf = Path(dir_nfe_pdf) / ano_mes
            caminho_nfe_pdf = pasta_nfe_pdf / f"{chave}-nfe.pdf"
            if not caminho_nfe_pdf.exists():
                caminho_nfe_pdf_alt = pasta_nfe_pdf / f"{chave}-nfe.PDF"
                if caminho_nfe_pdf_alt.exists():
                    caminho_nfe_pdf = caminho_nfe_pdf_alt

            if caminho_nfe_pdf.exists():
                arquivos_encontrados["NFE_PDF"] = str(caminho_nfe_pdf)

        # NFe XML: DIR_NFE_XML \ AnoMes \ NFe \ ChaveAcesso-nfe.xml
        dir_nfe_xml = caminhos_config.get("DIR_NFE_XML")
        if dir_nfe_xml:
            pasta_nfe_xml = Path(dir_nfe_xml) / ano_mes / "NFe"
            caminho_nfe_xml = pasta_nfe_xml / f"{chave}-nfe.xml"
            if not caminho_nfe_xml.exists():
                caminho_nfe_xml_alt = pasta_nfe_xml / f"{chave}-nfe.XML"
                if caminho_nfe_xml_alt.exists():
                    caminho_nfe_xml = caminho_nfe_xml_alt

            if caminho_nfe_xml.exists():
                arquivos_encontrados["NFE_XML"] = str(caminho_nfe_xml)

    return arquivos_encontrados