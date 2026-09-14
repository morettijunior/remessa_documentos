from app import carregar_ou_configurar_caminhos
from bd import consultar_pedido
from boleto import gerar_pdf_boleto
from arquivos import verificar_arquivos_pedido
from envio_email import enviar_email_cobranca

def rodar_teste_pedido():
    print("=" * 60)
    print("INICIANDO TESTE COMPLETO - PEDIDO 32309")
    print("=" * 60)

    # 1. Carrega as configurações de diretórios salvas no JSON de Documentos
    print("\n[1/5] Carregando caminhos configurados...")
    caminhos_config = carregar_ou_configurar_caminhos()

    # 2. Busca os dados completos do pedido 32309 direto do banco Firebird
    numero_pedido_teste = "32309"
    print(f"\n[2/5] Consultando dados do pedido {numero_pedido_teste} no banco de dados...")
    dados_pedido = consultar_pedido(numero_pedido_teste)

    if not dados_pedido:
        print(f"❌ Erro: Pedido {numero_pedido_teste} não foi encontrado no banco de dados.")
        return

    print(f"✔ Cliente encontrado: {dados_pedido.get('CLIENTE_NOME')}")
    print(f"✔ E-mail de destino: {dados_pedido.get('EMAIL')}")
    print(f"✔ Chave NFe: {dados_pedido.get('CHAVEACESSO_NFE')}")
    print(f"✔ NFS: {dados_pedido.get('NFS')}")
    print(f"✔ Quantidade de boletos na FLAN: {len(dados_pedido.get('BOLETOS', []))}")

    # Sobrescreve temporariamente o e-mail para você receber e testar a chegada/regra com segurança
    # (Comente a linha abaixo se quiser enviar para o e-mail real do cliente cadastrado no ERP)
    dados_pedido["EMAIL"] = "financeiro@rondochassis.com.br"

    # 3. Gera o PDF do boleto na pasta configurada
    print(f"\n[3/5] Gerando PDF(s) do boleto...")
    pasta_boletos = caminhos_config["DIR_PDF_BOLETO"]
    caminhos_boletos_gerados = gerar_pdf_boleto(dados_pedido, pasta_boletos)
    print(f"✔ Boletos gerados: {caminhos_boletos_gerados}")

    # 4. Varre, valida e retorna os caminhos reais de todos os arquivos no disco
    print(f"\n[4/5] Verificando e validando arquivos no disco (arquivos.py)...")
    arquivos_encontrados = verificar_arquivos_pedido(dados_pedido, caminhos_config)
    
    # Adiciona os boletos recém-gerados na lista de anexos
    arquivos_encontrados["BOLETOS"] = caminhos_boletos_gerados

    print("\nRelatório de Arquivos Encontrados:")
    for tipo, caminho in arquivos_encontrados.items():
        print(f"  - {tipo}: {caminho}")

    # 5. Configurações de Acesso ao SMTP da Hostinger
    config_email = {
        "smtp_host": "smtp.hostinger.com",
        "smtp_port": 465,
        "remetente": "financeiro@rondochassis.com.br",
        "senha": "rondoCh@ss1s"  # Altere se houver senha específica no seu ambiente
    }

    print(f"\n[5/5] Enviando e-mail de cobrança (envio_email.py)...")
    try:
        sucesso = enviar_email_cobranca(dados_pedido, arquivos_encontrados, config_email)
        if sucesso:
            print("\n" + "=" * 60)
            print("✅ SUCESSO! E-mail enviado e cópia disparada para acionar a regra.")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Erro crítico no envio do e-mail: {e}")

if __name__ == "__main__":
    rodar_teste_pedido()