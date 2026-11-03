# ARIS / MASTEN Windows desktop

Esta adaptação foi desenvolvida **dentro do fork do JARVIS do Matheus**. Os arquivos originais do JARVIS continuam no repositório e não foram substituídos.

## Como instalar

**Opção A: executável do GitHub Actions**

Abra a aba **Actions** do repositório, selecione **ARIS MASTEN Windows build**, abra a execução mais recente que terminou com sucesso e baixe o artefato `ARIS-MASTEN-Windows`. Extraia o executável e abra no Windows 11. O programa exige **Ollama instalado** e o modelo `qwen2.5:3b` baixado (`ollama pull qwen2.5:3b`). O modelo Vosk está embutido no executável da compilação do GitHub Actions.

**Opção B: instalar e executar pelo código-fonte**

Instale Python 3.12 e Ollama. Baixe o repositório pelo GitHub e execute `aris_masten/INSTALLAR_WINDOWS.bat`. O instalador baixa dependências, o Qwen2.5 3B e o modelo de fala em português. Depois use `aris_masten/start_windows.bat`.

## O que o aplicativo faz

- Interface desktop Windows, perfis ARIS e MASTEN selecionados pelo nome.
- Reconhecimento local de voz com Vosk em gravações de 8 segundos; também aceita texto digitado.
- Qwen2.5 3B pelo Ollama, com histórico curto por perfil salvo em `%LOCALAPPDATA%/ARIS_MASTEN/history.json`.
- ARIS: voz masculina Antonio Neural, mais grave.
- MASTEN: voz masculina Fabio Neural, mais leve e amigável.
- Respostas em voz via Edge TTS, que requer conexão à internet.
- Ferramentas locais: hora/data e abertura de calculadora, bloco de notas e explorador, após confirmação visual.

## Limitações importantes

- **Não é o Claude Code original**: as ferramentas MCP/skills do Matheus não estão disponíveis automaticamente no Ollama.
- Não há conexão autenticada com Gmail, WhatsApp, Spotify ou GitHub.
- Fish Audio não está conectado nesta versão; usa Edge TTS para ambas as vozes.
- O microfone usa botão de gravação de 8 segundos, **não** escuta contínua com wake word.
- O executável é gerado pelo GitHub Actions; esta versão ainda não foi validada num PC Windows real.
- Não publique senhas nem tokens no repositório.

## Base e licença

Fork de [matheustillimt-tech/jarvis](https://github.com/matheustillimt-tech/jarvis), licença MIT. Os módulos `aris_masten/` são a adaptação Windows independente sobre a estrutura do fork.
