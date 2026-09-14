import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
import json
from pathlib import Path
import threading

# Importação dos módulos do nosso sistema
from bd import consultar_pedido
from boleto import gerar_pdf_boleto
from arquivos import verificar_arquivos_pedido
from envio_email import enviar_email_cobranca
from envio_whatsapp import enviar_whatsapp_cobranca

# Configuração do arquivo de caminhos persistente
CONFIG_DIR = Path.home() / "Documents" / "RemessaDocumentos"
CONFIG_FILE = CONFIG_DIR / "config_caminhos.json"

def carregar_caminhos_salvos():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "DIR_PEDIDO": "",
        "DIR_NFS_PDF": "",
        "DIR_NFS_XML": "",
        "DIR_NFE_PDF": "",
        "DIR_NFE_XML": "",
        "DIR_PDF_BOLETO": str(Path.home() / "Documents" / "BoletosGerados")
    }

def salvar_caminhos_no_disco(caminhos):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(caminhos, f, indent=4, ensure_ascii=False)


class AppRemessa:
    def __init__(self, root):
        self.root = root
        self.root.title("Rondochassis - Central de Remessa de Documentos")
        self.root.geometry("750x600")
        self.root.minsize(700, 550)

        self.caminhos = carregar_caminhos_salvos()
        self.log_detalhado_texto = ""

        self.criar_widgets()

    def registrar_log(self, texto):
        print(texto)
        self.log_detalhado_texto += texto + "\n"

    def criar_widgets(self):
        # --- TÍTULO PRINCIPAL ---
        lbl_titulo = tk.Label(self.root, text="AUTOMAÇÃO DE COBRANÇA E REMESSA", font=("Arial", 14, "bold"), fg="#333")
        lbl_titulo.pack(pady=10)

        # --- FRAME DE ENTRADA DE DADOS ---
        frame_inputs = tk.LabelFrame(self.root, text=" Seleção de Pedidos e Canais ", font=("Arial", 10, "bold"), padx=15, pady=15)
        frame_inputs.pack(fill="x", padx=20, pady=10)

        # E-mail
        lbl_email = tk.Label(frame_inputs, text="ENVIAR PEDIDOS VIA E-MAIL (separados por vírgula):", font=("Arial", 9))
        lbl_email.pack(anchor="w")
        self.entry_email = tk.Entry(frame_inputs, font=("Arial", 10))
        self.entry_email.pack(fill="x", pady=(2, 10))

        # WhatsApp
        lbl_zap = tk.Label(frame_inputs, text="ENVIAR PEDIDOS VIA WHATSAPP (separados por vírgula):", font=("Arial", 9))
        lbl_zap.pack(anchor="w")
        self.entry_zap = tk.Entry(frame_inputs, font=("Arial", 10))
        self.entry_zap.pack(fill="x", pady=(2, 10))

        # --- FRAME DE BOTÕES DE AÇÃO ---
        frame_acoes = tk.Frame(self.root, pady=10)
        frame_acoes.pack(fill="x", padx=20)

        self.btn_executar = tk.Button(frame_acoes, text="▶ EXECUTAR DISPAROS", font=("Arial", 11, "bold"), bg="#28a745", fg="white", padx=20, pady=8, command=self.iniciar_processamento_thread)
        self.btn_executar.pack(side="left", expand=True, fill="x", padx=(0, 10))

        btn_config = tk.Button(frame_acoes, text="⚙ Configurar Pastas", font=("Arial", 10), padx=10, pady=8, command=self.abrir_janela_configuracoes)
        btn_config.pack(side="right")

        # --- RODAPÉ DISCRETO (LOG TÉCNICO) ---
        frame_rodape = tk.Frame(self.root, pady=10)
        frame_rodape.pack(side="bottom", fill="x", padx=20)

        self.btn_log = tk.Button(frame_rodape, text="🔍 Log Técnico", font=("Arial", 8), fg="#666", relief="flat", command=self.abrir_janela_log)
        self.btn_log.pack(side="right")

    def abrir_janela_configuracoes(self):
        janela_cfg = tk.Toplevel(self.root)
        janela_cfg.title("Configuração de Diretórios")
        janela_cfg.geometry("600x400")
        janela_cfg.grab_set()

        entries = {}
        chaves = [
            ("DIR_PEDIDO", "Pasta de Pedidos (PDF):"),
            ("DIR_NFS_PDF", "Pasta Nota Fiscal de Serviço (PDF):"),
            ("DIR_NFS_XML", "Pasta Nota Fiscal de Serviço (XML):"),
            ("DIR_NFE_PDF", "Pasta Nota Fiscal de Produto (PDF):"),
            ("DIR_NFE_XML", "Pasta Nota Fiscal de Produto (XML):"),
            ("DIR_PDF_BOLETO", "Pasta de Saída dos Boletos (PDF):")
        ]

        for idx, (chave, label_txt) in enumerate(chaves):
            lbl = tk.Label(janela_cfg, text=label_txt, font=("Arial", 9))
            lbl.grid(row=idx*2, column=0, sticky="w", padx=15, pady=(10, 0))

            ent = tk.Entry(janela_cfg, width=65, font=("Arial", 9))
            ent.insert(0, self.caminhos.get(chave, ""))
            ent.grid(row=idx*2+1, column=0, padx=15, pady=(0, 5))
            entries[chave] = ent

            def escolher_pasta(e=ent):
                pasta = filedialog.askdirectory()
                if pasta:
                    e.delete(0, tk.END)
                    e.insert(0, pasta)

            btn_browse = tk.Button(janela_cfg, text="Procurar...", command=escolher_pasta)
            btn_browse.grid(row=idx*2+1, column=1, padx=5)

        def salvar():
            for chave, ent in entries.items():
                self.caminhos[chave] = ent.get().strip()
            salvar_caminhos_no_disco(self.caminhos)
            messagebox.showinfo("Sucesso", "Caminhos salvos com sucesso!", parent=janela_cfg)
            janela_cfg.destroy()

        btn_salvar = tk.Button(janela_cfg, text="Salvar Configurações", font=("Arial", 10, "bold"), bg="#007bff", fg="white", command=salvar)
        btn_salvar.grid(row=len(chaves)*2, column=0, columnspan=2, pady=20)

    def abrir_janela_log(self):
        janela_log = tk.Toplevel(self.root)
        janela_log.title("Log Técnico de Execução (Programador)")
        janela_log.geometry("700x450")
        janela_log.grab_set()

        txt_log = scrolledtext.ScrolledText(janela_log, wrap=tk.WORD, font=("Courier New", 9))
        txt_log.pack(fill="both", expand=True, padx=10, pady=10)
        txt_log.insert(tk.END, self.log_detalhado_texto if self.log_detalhado_texto else "Nenhum log registrado nesta sessão.")
        txt_log.config(state=tk.DISABLED)

    def iniciar_processamento_thread(self):
        self.btn_executar.config(state=tk.DISABLED, text="PROCESSANDO...")
        self.log_detalhado_texto = "" # Limpa o log anterior
        
        # Roda em thread separada para não travar a interface gráfica do Windows
        threading.Thread(target=self.processar_lotes, daemon=True).start()

    def processar_lotes(self):
        pedidos_email_raw = self.entry_email.get().strip()
        pedidos_zap_raw = self.entry_zap.get().strip()

        lista_emails = [p.strip() for p in pedidos_email_raw.split(",") if p.strip()]
        lista_zaps = [p.strip() for p in pedidos_zap_raw.split(",") if p.strip()]

        if not lista_emails and not lista_zaps:
            self.root.after(0, lambda: messagebox.showwarning("Aviso", "Informe ao menos um número de pedido para E-mail ou WhatsApp."))
            self.root.after(0, lambda: self.btn_executar.config(state=tk.NORMAL, text="▶ EXECUTAR DISPAROS"))
            return

        config_email = {
            "smtp_host": "smtp.hostinger.com",
            "smtp_port": 465,
            "imap_host": "imap.hostinger.com",
            "imap_port": 993,
            "remetente": "financeiro@rondochassis.com.br",
            "senha": "rondoCh@ss1s"
        }

        resultados_email = []
        resultados_zap = []

        # ==========================================
        # 1. PROCESSAMENTO DE E-MAILS
        # ==========================================
        if lista_emails:
            self.registrar_log("=== INICIANDO LOTE DE E-MAILS ===")
            for num_pedido in lista_emails:
                self.registrar_log(f"\n[E-mail] Processando pedido: {num_pedido}")
                try:
                    dados_pedido = consultar_pedido(num_pedido)
                    if not dados_pedido:
                        raise ValueError(f"Pedido {num_pedido} não encontrado no banco de dados Firebird.")

                    if not dados_pedido.get("EMAIL"):
                        raise ValueError(f"Cliente '{dados_pedido.get('CLIENTE_NOME')}' não possui e-mail cadastrado.")

                    # Gera boletos
                    pasta_boletos = self.caminhos.get("DIR_PDF_BOLETO")
                    if not pasta_boletos:
                        raise ValueError("Diretório de saída dos boletos não configurado.")
                    caminhos_boletos = gerar_pdf_boleto(dados_pedido, pasta_boletos)

                    # Valida arquivos obrigatórios
                    arquivos = verificar_arquivos_pedido(dados_pedido, self.caminhos)
                    arquivos["BOLETOS"] = caminhos_boletos

                    # Blindagem de arquivos: Verifica se falta algum arquivo essencial mapeado
                    falhas_arquivos = []
                    if not arquivos.get("PEDIDO"): falhas_arquivos.append("Pedido PDF")
                    if not arquivos.get("NFS_PDF") and not arquivos.get("NFE_PDF"): falhas_arquivos.append("Nota Fiscal (PDF)")
                    if not caminhos_boletos: falhas_arquivos.append("Boleto (PDF)")

                    if falhas_arquivos:
                        raise ValueError(f"Arquivos obrigatórios faltando no disco: {', '.join(falhas_arquivos)}. Envio cancelado.")

                    # Dispara E-mail
                    enviar_email_cobranca(dados_pedido, arquivos, config_email)
                    self.registrar_log(f"[E-mail] Sucesso para o pedido {num_pedido}")
                    resultados_email.append((num_pedido, True, "Enviado com sucesso"))

                except Exception as e:
                    erro_msg = str(e)
                    self.registrar_log(f"[E-mail] FALHA no pedido {num_pedido}: {erro_msg}")
                    resultados_email.append((num_pedido, False, erro_msg))

        # ==========================================
        # 2. PROCESSAMENTO DE WHATSAPP
        # ==========================================
        if lista_zaps:
            self.registrar_log("\n=== INICIANDO LOTE DE WHATSAPP ===")
            driver_zap = None
            try:
                # Inicializa o Edge uma única vez para o lote todo
                from selenium import webdriver
                from selenium.webdriver.edge.service import Service as EdgeService
                from webdriver_manager.microsoft import EdgeChromiumDriverManager

                pasta_perfil = Path.home() / "Documents" / "RemessaDocumentos" / "WhatsappSessionEdge"
                pasta_perfil.mkdir(parents=True, exist_ok=True)

                options = webdriver.EdgeOptions()
                options.add_argument(f"user-data-dir={pasta_perfil}")
                options.add_argument("--start-maximized")

                self.registrar_log("Iniciando Microsoft Edge para WhatsApp...")
                driver_zap = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

            except Exception as e:
                msg_erro_driver = f"Erro ao inicializar navegador Edge para WhatsApp: {e}"
                self.registrar_log(msg_erro_driver)
                for num_pedido in lista_zaps:
                    resultados_zap.append((num_pedido, False, msg_erro_driver))
                driver_zap = None

            if driver_zap:
                for num_pedido in lista_zaps:
                    self.registrar_log(f"\n[WhatsApp] Processando pedido: {num_pedido}")
                    try:
                        dados_pedido = consultar_pedido(num_pedido)
                        if not dados_pedido:
                            raise ValueError(f"Pedido {num_pedido} não encontrado no banco de dados Firebird.")

                        telefone_raw = dados_pedido.get("WHATSAPP") or dados_pedido.get("TELEFONE")
                        if not telefone_raw:
                            raise ValueError(f"Cliente '{dados_pedido.get('CLIENTE_NOME')}' não possui número de WhatsApp válido.")

                        # Gera boletos (necessário para extrair Pix e Linha Digitável para o texto)
                        pasta_boletos = self.caminhos.get("DIR_PDF_BOLETO")
                        caminhos_boletos = gerar_pdf_boleto(dados_pedido, pasta_boletos)
                        
                        arquivos = verificar_arquivos_pedido(dados_pedido, self.caminhos)
                        arquivos["BOLETOS"] = caminhos_boletos

                        # Validação de arquivos essenciais antes do envio informativo
                        if not caminhos_boletos:
                            raise ValueError("Boleto não gerado. Impossível enviar dados de pagamento via WhatsApp.")

                        # Dispara aviso informativo estruturado no WhatsApp (sem anexos instáveis)
                        enviar_whatsapp_cobranca(dados_pedido, driver_instancia=driver_zap)
                        self.registrar_log(f"[WhatsApp] Sucesso para o pedido {num_pedido}")
                        resultados_zap.append((num_pedido, True, "Enviado com sucesso"))

                    except Exception as e:
                        erro_msg = str(e)
                        self.registrar_log(f"[WhatsApp] FALHA no pedido {num_pedido}: {erro_msg}")
                        resultados_zap.append((num_pedido, False, erro_msg))

                try:
                    driver_zap.quit()
                    self.registrar_log("Navegador Edge do WhatsApp fechado com segurança.")
                except:
                    pass

        # Exibe relatório amigável ao usuário
        self.root.after(0, lambda: self.exibir_relatorio_final(resultados_email, resultados_zap))
        self.root.after(0, lambda: self.btn_executar.config(state=tk.NORMAL, text="▶ EXECUTAR DISPAROS"))

    def exibir_relatorio_final(self, res_email, res_zap):
        relatorio = "RELATÓRIO DE PROCESSAMENTO DO LOTE\n" + "="*40 + "\n\n"

        if res_email:
            relatorio += "--- E-MAILS ---\n"
            for ped, status, motivo in res_email:
                res_txt = "SUCESSO" if status else f"FALHA ({motivo})"
                relatorio += f"• Pedido {ped}: {res_txt}\n"
            relatorio += "\n"

        if res_zap:
            relatorio += "--- WHATSAPP ---\n"
            for ped, status, motivo in res_zap:
                res_txt = "SUCESSO" if status else f"FALHA ({motivo})"
                relatorio += f"• Pedido {ped}: {res_txt}\n"

        messagebox.showinfo("Processamento Concluído", relatorio)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppRemessa(root)
    root.mainloop()