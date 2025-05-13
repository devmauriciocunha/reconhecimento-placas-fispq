import os
import re
import csv
import sqlite3
import json
from PyPDF2 import PdfReader

class FISPQExtractor:
    def __init__(self, db_path='dados_fispq.db', csv_path='dados_fispq.csv', json_dir='dados_json', pdf_dir=r'C:/Users/mauri/OneDrive/Área de Trabalho/extraindoDados/FISPQ'):
        """Inicializa as variáveis e cria o banco de dados e diretórios necessários"""
        self.db_path = db_path
        self.csv_path = csv_path
        self.json_dir = json_dir
        self.pdf_dir = pdf_dir  # Diretório onde os PDFs serão lidos
        self._create_table()
        self._create_json_dir()

    def _create_table(self):
        """Cria a tabela no banco de dados se não existir"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
                CREATE TABLE IF NOT EXISTS fispq (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    substancia TEXT,
                    numero_onu TEXT,
                    numero_risco TEXT,
                    classe TEXT,
                    risco_subsidiario TEXT,
                    primeiros_socorros TEXT,
                    medidas_incendio TEXT,
                    medidas_fuga TEXT,
                    arquivo TEXT
                );
            """)
            conn.commit()

    def _create_json_dir(self):
        """Cria o diretório para salvar os arquivos JSON, caso não exista"""
        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)

    def extract_info(self, text):
        """Extraí os dados essenciais do texto extraído do PDF"""
        def match(pattern, group=1):
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            return m.group(group).strip() if m else None

        return {
            "substancia": match(r"(?:Nome do produto|Substância)\s*[:\-]?\s*([^\n:]+)"),
            "numero_onu": match(r"(?i)(?:Número ONU|ONU)\s*[:\-]?\s*(\d{4,5})"),  # Ajuste na regex para pegar o número ONU
            "numero_risco": match(r"(?:Número de Risco|Risco)\s*[:\-]?\s*(\d+)"),
            "classe": match(r"Classe\s*\/\s*subclasse\s*de\s*risco\s*principal\s*e\s*subsidiário\s*[:\-]?\s*(\d+(\.\d+)?)\s*(?:\((\d+)\))?"),
            "risco_subsidiario": match(r"(?:Risco Subsidiário|Subsidiário)\s*[:\-]?\s*([^\n]+)"),
            "primeiros_socorros": match(r"(?:4\.\s*PRIMEIROS SOCORROS|PRIMEIROS SOCORROS)(.*?)(?=\d+\.\s|\Z)"),
            "medidas_incendio": match(r"(?:5\.\s*MEDIDAS DE COMBATE A INCÊNDIO|COMBATE A INCÊNDIO)(.*?)(?=\d+\.\s|\Z)"),
            "medidas_fuga": match(r"(?:6\.\s*MEDIDAS A TOMAR EM CASO DE FUGAS ACIDENTAIS|FUGAS ACIDENTAIS)(.*?)(?=\d+\.\s|\Z)"),
        }

    def process_pdf(self, pdf_path):
        """Processa o PDF e extrai os dados essenciais"""
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)

        info = self.extract_info(text)
        info['arquivo'] = os.path.basename(pdf_path)

        if info:
            # Verificar se o arquivo JSON já existe
            json_filename = os.path.join(self.json_dir, f"{os.path.splitext(info['arquivo'])[0]}.json")
            if not os.path.exists(json_filename):
                self._save_to_db(info)
                self._save_to_csv(info)
                self._save_to_json(info)  # Salvar os dados extraídos como JSON
            else:
                print(f"⚠️ O arquivo JSON já existe: {json_filename}. Não foi substituído.")

    def _save_to_db(self, data):
        """Salva ou atualiza os dados no banco de dados"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM fispq WHERE arquivo = ?", (data["arquivo"],))
                existing_data = cursor.fetchone()

                if existing_data:
                    cursor.execute(""" 
                        UPDATE fispq SET 
                            substancia = ?, 
                            numero_onu = ?, 
                            numero_risco = ?, 
                            classe = ?, 
                            risco_subsidiario = ?, 
                            primeiros_socorros = ?, 
                            medidas_incendio = ?, 
                            medidas_fuga = ? 
                        WHERE arquivo = ?
                    """, (
                        data["substancia"],
                        data["numero_onu"],
                        data["numero_risco"],
                        data["classe"],
                        data["risco_subsidiario"],
                        data["primeiros_socorros"],
                        data["medidas_incendio"],
                        data["medidas_fuga"],
                        data["arquivo"]
                    ))
                    print(f"✅ Dados atualizados no banco: {data['arquivo']}")
                else:
                    cursor.execute(""" 
                        INSERT INTO fispq (
                            substancia, numero_onu, numero_risco, classe,
                            risco_subsidiario, primeiros_socorros,
                            medidas_incendio, medidas_fuga, arquivo
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data["substancia"],
                        data["numero_onu"],
                        data["numero_risco"],
                        data["classe"],
                        data["risco_subsidiario"],
                        data["primeiros_socorros"],
                        data["medidas_incendio"],
                        data["medidas_fuga"],
                        data["arquivo"]
                    ))
                    print(f"✅ Dados inseridos no banco: {data['arquivo']}")
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"❌ Erro ao inserir ou atualizar dados no banco: {e}")

    def _save_to_csv(self, data):
        """Salva os dados em um arquivo CSV"""
        try:
            file_exists = os.path.isfile(self.csv_path)
            with open(self.csv_path, mode='a', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(data)
        except Exception as e:
            print(f"❌ Erro ao salvar no CSV: {e}")

    def _save_to_json(self, data):
        """Salva os dados extraídos de cada PDF em um arquivo JSON"""
        try:
            json_filename = os.path.join(self.json_dir, f"{os.path.splitext(data['arquivo'])[0]}.json")
            with open(json_filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
            print(f"✅ Dados salvos no JSON: {json_filename}")
        except Exception as e:
            print(f"❌ Erro ao salvar no JSON: {e}")

    def importar_json_para_db(self):
        """Importa os dados de um arquivo JSON para o banco de dados e atualiza as informações existentes"""
        try:
            for json_file in os.listdir(self.json_dir):
                if json_file.lower().endswith('.json'):
                    json_path = os.path.join(self.json_dir, json_file)
                    with open(json_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        self._save_to_db(data)
                        print(f"✅ Banco de dados atualizado a partir do JSON: {json_file}")
        except Exception as e:
            print(f"❌ Erro ao importar dados dos JSONs para o banco: {e}")

    def importar_json_manual_para_db(self):
        """Importa os dados de um arquivo JSON editado manualmente para o banco de dados"""
        try:
            for json_file in os.listdir(self.json_dir):
                if json_file.lower().endswith('.json'):
                    json_path = os.path.join(self.json_dir, json_file)
                    with open(json_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        self._save_to_db(data)
                        print(f"✅ Banco de dados atualizado a partir do JSON manual: {json_file}")
        except Exception as e:
            print(f"❌ Erro ao importar dados do JSON manual para o banco: {e}")

class FISPQApp:
    def __init__(self):
        self.extractor = FISPQExtractor()

    def display_menu(self):
        """Exibe o menu e processa a escolha do usuário"""
        while True:
            print("\n----- MENU -----")
            print("1. Processar PDFs")
            print("2. Exibir dados no banco")
            print("3. Excluir dado (por ID)")
            print("4. Sair")
            
            choice = input("Escolha uma opção (1-4): ")
            
            if choice == "1":
                self.process_pdfs()
            elif choice == "2":
                self.show_data()
            elif choice == "3":
                self.delete_data()
            elif choice == "4":
                print("Saindo...")
                break
            else:
                print("Opção inválida. Tente novamente.")

    def process_pdfs(self):
        """Processa PDFs do diretório especificado e extrai dados"""
        self.extractor.process_pdf(self.extractor.pdf_dir)

    def show_data(self):
        """Exibe os dados no banco de dados"""
        try:
            with sqlite3.connect(self.extractor.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM fispq")
                rows = cursor.fetchall()

                if rows:
                    print("\nDados no banco de dados:")
                    for row in rows:
                        print(row)  # Exibe todos os dados no banco, incluindo o ID
                else:
                    print("Nenhum dado encontrado no banco.")
        except sqlite3.Error as e:
            print(f"❌ Erro ao exibir os dados: {e}")

    def delete_data(self):
        """Exclui dados do banco de dados com confirmação por ID"""
        try:
            self.show_data()  # Exibe os dados antes de excluir
            id_to_delete = input("\nDigite o ID do dado que deseja excluir: ")

            # Confirmação antes de excluir
            confirm = input(f"Tem certeza que deseja excluir o dado com ID '{id_to_delete}'? (s/n): ").lower()
            if confirm != 's':
                print("❌ A exclusão foi cancelada.")
                return

            with sqlite3.connect(self.extractor.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM fispq WHERE id = ?", (id_to_delete,))
                existing_data = cursor.fetchone()

                if existing_data:
                    cursor.execute("DELETE FROM fispq WHERE id = ?", (id_to_delete,))
                    conn.commit()
                    print(f"✅ Dados excluídos com sucesso! ID: {id_to_delete}")
                else:
                    print(f"❌ Dado com ID '{id_to_delete}' não encontrado no banco.")

        except sqlite3.Error as e:
            print(f"❌ Erro ao excluir dados: {e}")

if __name__ == "__main__":
    app = FISPQApp()
    app.display_menu()
