import os
from extractor import FISPQExtractor
import sqlite3

class FISPQApp:
    def __init__(self):
        self.extractor = FISPQExtractor()

    def display_menu(self):
        """Exibe o menu e processa a escolha do usuário."""
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
        """Processa PDFs do diretório especificado e extrai dados."""
        input_dir = r"C:/Users/mauri/OneDrive/Área de Trabalho/extraindoDados"
        pdfs = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]

        if not pdfs:
            print("Nenhum PDF encontrado no diretório.")
            return

        print(f"{len(pdfs)} arquivos encontrados. Processando...\n")

        for pdf_file in pdfs:
            try:
                path = os.path.join(input_dir, pdf_file)
                self.extractor.process_pdf(path)
                print(f"✔ Processado: {pdf_file}")
            except Exception as e:
                print(f"❌ Erro ao processar {pdf_file}: {e}")

        print("\n✅ Extração finalizada.")

    def show_data(self):
        """Exibe os dados no banco de dados."""
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
        """Exclui dados do banco de dados com confirmação por ID."""
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
