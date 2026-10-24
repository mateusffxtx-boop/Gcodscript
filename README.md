# Gcodscript AI — Android

Chatbot em português usando Flet e a Gemini API.

## Segurança
- Nunca coloque a chave da API no código, no README ou em arquivos do GitHub.
- O app pede a chave na tela e a mantém apenas em memória durante a sessão.
- Se uma chave já apareceu em uma captura pública, revogue-a e crie outra.

## Gerar o APK pelo celular
1. Envie os arquivos desta pasta para a raiz do repositório `mateusffxtx-boop/Gcodscript`, mantendo a estrutura de pastas.
2. Abra a aba **Actions** do repositório.
3. Se necessário, habilite GitHub Actions.
4. A workflow **Build Android APK** começa automaticamente após um push; também pode ser iniciada manualmente com **Run workflow**.
5. Quando terminar com sucesso, abra a execução e baixe `gcodscript-ai-apk` na seção **Artifacts**.
6. Extraia o ZIP do artefato e instale o APK no Android. Instale apenas um APK que você mesmo gerou e revise os resultados da compilação.

## Dependências
O Flet é instalado pela configuração do projeto. A compilação é executada em um runner hospedado pelo GitHub.

## Observações
- O primeiro build pode demorar.
- O nome do modelo usado é `gemini-2.5-flash`; disponibilidade e limites dependem da conta/projeto da Gemini API.
- Este projeto é uma base inicial. Ainda precisa ser compilado e testado no dispositivo real.
