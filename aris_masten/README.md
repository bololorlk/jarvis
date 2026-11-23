# ARIS / MASTEN Windows desktop

Esta adaptação foi desenvolvida **dentro do fork do JARVIS do Matheus**. Os arquivos originais do JARVIS continuam no repositório e não foram substituídos.

## Como instalar

**Opção A: executável do GitHub Actions**

Abra a aba **Actions** do repositório, selecione **ARIS MASTEN Windows build**, abra a execução mais recente que terminou com sucesso e baixe o artefato `ARIS-MASTEN-Windows`. Extraia o executável e abra no Windows 11. O programa exige **Ollama instalado** e o modelo `qwen2.5:3b` baixado (`ollama pull qwen2.5:3b`). O modelo Vosk está embutido no executável da compilação do GitHub Actions.

**Opção B: instalar e executar pelo código-fonte**

Instale Python 3.12 e Ollama. Baixe o repositório pelo GitHub e execute `aris_masten/INSTALLAR_WINDOWS.bat`. O instalador baixa dependências, o Qwen2.5 3B e o modelo de fala em português. Depois use `aris_masten/start_windows.bat`.

## O que o aplicativo faz

- Interface desktop Windows, perfis ARIS e MASTEN selecionados pelo nome.
- Microfone automático com reconhecimento local Vosk: diga "ARIS" ou "MASTEN" seguido de um pedido, ou diga o nome e faça o pedido nos próximos 10 segundos.
- Comando direto para ajustar o volume principal do Windows, por exemplo: "ARIS, aumente o volume para 75%".
- Qwen2.5 3B pelo Ollama, com histórico curto por perfil salvo em `%LOCALAPPDATA%/ARIS_MASTEN/history.json`.
- ARIS: voz masculina Antonio Neural, mais grave.
- MASTEN: voz masculina Fabio Neural, mais leve e amigável.
- Respostas em voz via Edge TTS, que requer conexão à internet.
- Ferramentas locais: hora/data e abertura direta de calculadora, bloco de notas e explorador, sem confirmação. Outras ações não são liberadas automaticamente.

## Limitações importantes

- **Não é o Claude Code original**: as ferramentas MCP/skills do Matheus não estão disponíveis automaticamente no Ollama.
- Não há conexão autenticada com Gmail, WhatsApp, Spotify ou GitHub.
- Fish Audio não está conectado nesta versão; usa Edge TTS para ambas as vozes.
- O reconhecimento usa frases de até 7 segundos, em escuta contínua. Os nomes são reconhecidos pelo Vosk, não por um detector dedicado de wake word, podendo falhar em ambientes ruidosos.
- O executável é gerado pelo GitHub Actions; esta versão ainda não foi validada num PC Windows real.
- Não publique senhas nem tokens no repositório.

## Base e licença

Fork de [matheustillimt-tech/jarvis](https://github.com/matheustillimt-tech/jarvis), licença MIT. Os módulos `aris_masten/` são a adaptação Windows independente sobre a estrutura do fork.
