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

  # 1. Caminho do PDF do Pedido (Ex: C:\TGA\Pedidos\32231.pdf)
  if dados_pedido.get("NUMERO_PEDIDO"):
    caminho_pedido = (
        Path(caminhos_config["DIR_PDF_PEDIDO"])
        / f"{dados_pedido['NUMERO_PEDIDO']}.pdf"
    )
    if caminho_pedido.exists():
      arquivos_encontrados["PEDIDO"] = str(caminho_pedido)

  # 2. Caminho da NFS (Ex: \\Servidor\tga\NFS-e\XML\18836-nfse.pdf)
  if dados_pedido.get("NFS"):
    caminho_nfs = (
        Path(caminhos_config["DIR_NFS_PDF"])
        / f"{dados_pedido['NFS']}-nfse.pdf"
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

    # NFe XML: DIR_NFE_XML \ AnoMes \ NFe \ ChaveAcesso.xml
    caminho_nfe_xml = (
        Path(caminhos_config["DIR_NFE_XML"]) / ano_mes / "NFe" / f"{chave}.xml"
    )
    if caminho_nfe_xml.exists():
      arquivos_encontrados["NFE_XML"] = str(caminho_nfe_xml)

  return arquivos_encontrados