import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog


def obter_caminho_config():
    """Cria uma pasta dedicada em 'Documentos' do usuário e retorna o caminho do JSON."""
    pasta_documentos = Path.home() / "Documents" / "RemessaDocumentos"
    pasta_documentos.mkdir(parents=True, exist_ok=True)
    return pasta_documentos / "config_caminhos.json"


CONFIG_FILE = obter_caminho_config()


def selecionar_pasta(titulo):
    """Abre uma janela para o usuário selecionar a pasta visualmente."""
    root = tk.Tk()
    root.withdraw()
    caminho = filedialog.askdirectory(title=titulo)
    return caminho


def carregar_ou_configurar_caminhos():
    """Carrega do JSON em Documentos ou solicita ao usuário caso não exista."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            caminhos = json.load(f)

        print(f"Configuração carregada de: {CONFIG_FILE}")
        print("Caminhos atuais:")
        for chave, valor in caminhos.items():
            print(f" - {chave}: {valor}")

        alterar = (
            input(
                "\nDeseja manter esses caminhos ou reconfigurar? (manter/reconfigurar): "
            )
            .strip()
            .lower()
        )
        if alterar != "reconfigurar":
            return caminhos

    print("\n[Configuração Inicial] Por favor, selecione as pastas correspondentes:")

    caminhos = {
        "DIR_NFS_PDF": selecionar_pasta("Selecione a pasta de PDF das NFS-e"),
        "DIR_NFE_PDF": selecionar_pasta("Selecione a pasta de PDF das NFe"),
        "DIR_NFE_XML": selecionar_pasta("Selecione a pasta de XML das NFe"),
        "DIR_PDF_PEDIDO": selecionar_pasta("Selecione a pasta de PDF dos Pedidos"),
        "DIR_PDF_BOLETO": selecionar_pasta("Selecione a pasta onde salvar os Boletos gerados"),
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(caminhos, f, indent=4, ensure_ascii=False)

    print(f"Configurações salvas com sucesso em: {CONFIG_FILE}")
    return caminhos


def main():
    caminhos = carregar_ou_configurar_caminhos()

    # Variáveis de diretório dinâmicas prontas para uso no sistema
    DIR_NFS = caminhos["DIR_NFS_PDF"]
    DIR_NFE = caminhos["DIR_NFE_PDF"]
    DIR_XML = caminhos["DIR_NFE_XML"]
    DIR_PDF_PEDIDO = caminhos["DIR_PDF_PEDIDO"]
    DIR_PDF_BOLETO = caminhos["DIR_PDF_BOLETO"]

    print("\n=== SISTEMA PRONTO PARA USO ===")
    print(f"NFS: {DIR_NFS}")
    print(f"NFe PDF: {DIR_NFE}")
    print(f"NFe XML: {DIR_XML}")
    print(f"Pedidos: {DIR_PDF_PEDIDO}")
    print(f"Boletos: {DIR_PDF_BOLETO}")

    entrada_pedidos = input(
        "\nInsira o número dos pedidos separados por vírgula (ex: 32173, 24170): "
    )
    lista_pedidos = [p.strip() for p in entrada_pedidos.split(",")]

    enviar_email_flag = (
        input("Deseja enviar por E-MAIL? (s/n): ").strip().lower() == "s"
    )
    enviar_zap_flag = (
        input("Deseja enviar por WHATSAPP? (s/n): ").strip().lower() == "s"
    )


if __name__ == "__main__":
    main()