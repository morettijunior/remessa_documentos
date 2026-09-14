from app import carregar_ou_configurar_caminhos
from bd import consultar_pedido
from boleto import gerar_pdf_boleto
from arquivos import verificar_arquivos_pedido
from envio_whatsapp import enviar_whatsapp_cobranca

def rodar_teste_whatsapp():
    print("=" * 60)
    print("INICIANDO TESTE ISOLADO - WHATSAPP")
    print("=" * 60)

    # 1. Carrega as configurações de pastas
    print("\n[1/4] Carregando caminhos configurados...")
    caminhos_config = carregar_ou_configurar_caminhos()

    # 2. Busca os dados do pedido 32309 no Firebird
    numero_pedido_teste = "32309"
    print(f"\n[2/4] Consultando dados do pedido {numero_pedido_teste} no Firebird...")
    dados_pedido = consultar_pedido(numero_pedido_teste)

    if not dados_pedido:
        print(f"❌ Erro: Pedido {numero_pedido_teste} não encontrado no banco.")
        return

    print(f"✔ Cliente: {dados_pedido.get('CLIENTE_NOME')}")
    print(f"✔ WhatsApp cadastrado: {dados_pedido.get('WHATSAPP')}")

    # (Opcional) Descomente abaixo e coloque o seu número com DDD se quiser testar recebendo no seu celular:
    # dados_pedido["WHATSAPP"] = "66999999999"

    # 3. Gera os boletos na pasta configurada
    print(f"\n[3/4] Gerando PDF(s) do boleto...")
    pasta_boletos = caminhos_config["DIR_PDF_BOLETO"]
    caminhos_boletos_gerados = gerar_pdf_boleto(dados_pedido, pasta_boletos)
    print(f"✔ Boletos gerados: {caminhos_boletos_gerados}")

    # 4. Valida e localiza todos os arquivos no disco
    print(f"\n[4/4] Verificando arquivos no disco e disparando no WhatsApp...")
    arquivos_encontrados = verificar_arquivos_pedido(dados_pedido, caminhos_config)
    arquivos_encontrados["BOLETOS"] = caminhos_boletos_gerados

    print("\nArquivos Mapeados:")
    for tipo, caminho in arquivos_encontrados.items():
        print(f"  - {tipo}: {caminho}")

    # Disparo exclusivo via WhatsApp
    try:
        enviar_whatsapp_cobranca(dados_pedido, arquivos_encontrados)
        print("\n" + "=" * 60)
        print("✅ SUCESSO! WhatsApp disparado com os anexos.")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Erro no WhatsApp: {e}")

if __name__ == "__main__":
    rodar_teste_whatsapp()