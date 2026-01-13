# bloco-TG

**Um cliente Telegram "Stealth" disfarçado de Bloco de Notas do Windows.**

O **bloco-TG** é uma aplicação Python minimalista projetada para ambientes onde a discrição é fundamental. Ele imita perfeitamente a interface clássica do Bloco de Notas (Notepad), mas funciona como um cliente Telegram totalmente funcional.

![Screenshot](screenshot.png) *(Adicione uma captura de tela aqui se desejar)*

## 🚀 Funcionalidades

*   **Camuflagem Perfeita**: Interface idêntica ao Bloco de Notas. Título da janela muda para `*bloco-TG` apenas quando focado.
*   **Modo Stealth (F12/Esc)**: Miniminiza instantaneamente para a bandeja do sistema (System Tray) com um ícone discreto.
*   **Limpeza de Emergência (Ctrl+S)**: Limpa a tela de chat imediatamente, simulando um arquivo de texto em branco.
*   **Mensagens**:
    *   Envio e recebimento em tempo real.
    *   Confirmação de leitura estilo ASCII: `[v]` (Enviado) -> `[vv]` (Lido).
    *   Envio de arquivos e imagens.
*   **Privacidade**:
    *   Suporte a exclusão de mensagens para todos (Delete for Everyone).
    *   Arquivar e Silenciar conversas pelo menu de contexto.
    *   Não baixa mídia automaticamente (apenas sob demanda).
*   **Portátil**: Salva sessões e configurações na pasta local, ideal para rodar de pen drives.

## 🛠️ Instalação e Execução

### Pré-requisitos
*   Python 3.10+
*   Uma conta Telegram ativa.

### Instalação das Dependências

1.  Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/bloco-TG.git
    cd bloco-TG
    ```

2.  Instale os pacotes necessários:
    ```bash
    pip install telethon pillow pystray python-dotenv pyinstaller
    ```

### Como Usar

1.  **Primeira Execução**:
    Execute o arquivo principal:
    ```bash
    python main.py
    ```
    
2.  **Configuração Inicial**:
    *   Uma janela simples pedirá seu número de telefone (com DDI e DDD, ex: `+5511999999999`).
    *   Insira o código enviado pelo Telegram.
    *   (Se ativado) Insira sua senha de verificação em duas etapas (2FA).
    *   As credenciais serão salvas localmente em `config.ini` e o arquivo de sessão `bloco_tg.session`.

3.  **No Chat**:
    *   **Barra Lateral**: Lista seus contatos recentes (Top 10 privados).
    *   **Área de Texto**: Mostra o histórico. Digite sua mensagem na última linha e pressione `Enter` para enviar.
    *   **Botão Direito (Chat)**: Menu para enviar arquivos, limpar histórico ou excluir mensagens.
    *   **Botão Direito (Lateral)**: Marcar como lida, arquivar ou silenciar.

4.  **Atalhos de Teclado**:
    *   `F12` ou `Esc`: Esconder para a Bandeja.
    *   `Ctrl+S`: Limpeza de Emergência (Clear Screen).
    *   `Ctrl+N`: Pesquisar/Abrir nova conversa.
    *   `Alt+Seta Cima/Baixo`: Navegar entre contatos.

## 📦 Criando o Executável (Portátil)

Para gerar um arquivo `.exe` único que não precisa de Python instalado:

1.  Certifique-se de ter o `pyinstaller` instalado.
2.  Execute o script de build:
    ```bat
    .\build_portable.bat
    ```
3.  O executável será gerado na pasta `dist/`.

## ⚠️ Aviso Legal

Este projeto foi desenvolvido para fins educacionais e de produtividade pessoal. O uso deste software em ambientes corporativos deve estar em conformidade com as políticas da sua empresa. Os desenvolvedores não se responsabilizam pelo mau uso da ferramenta.

**Desenvolvido por Inside Soluções**
