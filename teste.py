import json
from arquivos import verificar_arquivos_pedido
from bd import consultar_pedido
from boleto import gerar_pdf_boleto


def testar_fluxo_completo(numero_pedido):
  print(f"=== INICIANDO TESTE COMPLETO PARA O PEDIDO: {numero_pedido} ===")

  # 1. Caminhos configurados
  caminhos_teste = {
      "DIR_NFS_PDF": r"\\Servidor\tga\NFS-e\XML",
      "DIR_NFE_PDF": r"C:\TGA\Nfe\PDF",
      "DIR_NFE_XML": r"C:\TGA\Nfe\XML",
      "DIR_PDF_PEDIDO": r"C:\TGA\Pedidos",
      "DIR_PDF_BOLETO": r"C:\TGA\Boletos\PDF",
  }

  # 2. Busca os dados no Banco Firebird (AQUI O DADOS_BD É CRIADO)
  print("\n[1/3] Consultando dados no banco Firebird...")
  dados_bd = consultar_pedido(numero_pedido)

  if not dados_bd:
    print(f"[ERRO] Pedido {numero_pedido} não encontrado ou falha na conexão.")
    return

  print("\n--- DADOS RETORNADOS DO BANCO ---")
  print(json.dumps(dados_bd, indent=4, ensure_ascii=False))

  # 3. Verifica a existência dos arquivos físicos nas pastas
  print("\n[2/3] Verificando arquivos físicos nas pastas configuradas...")
  arquivos = verificar_arquivos_pedido(dados_bd, caminhos_teste)

  print("\n--- STATUS DOS ARQUIVOS FÍSICOS ---")
  for tipo, caminho in arquivos.items():
    if tipo == "BOLETOS":
      continue
    status = f"ENCONTRADO -> {caminho}" if caminho else "NÃO ENCONTRADO ❌"
    print(f"  {tipo}: {status}")

  # 4. Gera os PDFs dos Boletos por parcela
  print("\n[3/3] Gerando PDFs dos Boletos...")
  pdfs_boletos = gerar_pdf_boleto(dados_bd, caminhos_teste["DIR_PDF_BOLETO"])
  
  print("\n--- BOLETOS GERADOS ---")
  for pdf in pdfs_boletos:
    print(f"  GERADO -> {pdf}")

  print("\n=== TESTE FINALIZADO COM SUCESSO ===")


if __name__ == "__main__":
  testar_fluxo_completo("32302")