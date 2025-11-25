const logPanel = document.getElementById('progressLog');
const heartbeatMessages = [
    'Processando com a IA... Pode levar alguns minutos.',
    'Ainda trabalhando no rascunho e revisão do conteúdo.',
    'Gerando PDF com layout final.',
    'Ainda em andamento: aguardando resposta do backend.'
];
let heartbeatTimer = null;

function appendLog(message) {
    if (!logPanel) return;
    const placeholder = logPanel.querySelector('.log-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    const row = document.createElement('div');
    row.className = 'log-entry';
    const timestamp = new Date().toLocaleTimeString('pt-BR', { hour12: false });
    row.textContent = `[${timestamp}] ${message}`;
    logPanel.appendChild(row);
    logPanel.scrollTop = logPanel.scrollHeight;
}

function clearLog() {
    if (logPanel) {
        logPanel.innerHTML = '';
    }
}

function startHeartbeat() {
    if (heartbeatTimer || !logPanel) return;
    let tick = 0;
    heartbeatTimer = window.setInterval(() => {
        const msg = heartbeatMessages[tick % heartbeatMessages.length];
        appendLog(msg);
        tick += 1;
    }, 15000);
}

function stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

document.getElementById('ebookForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const statusDiv = document.getElementById('status');
    const downloadSection = document.getElementById('downloadSection');
    clearLog();
    appendLog('Processo iniciado. Preparando os dados enviados.');

    // Resetar status
    statusDiv.className = 'status loading';
    statusDiv.textContent = 'Gerando seu ebook... Isso pode levar alguns minutos.';
    downloadSection.style.display = 'none';

    // Coletar dados do formulário
    const formData = new FormData();
    formData.append('google_api_key', document.getElementById('googleApiKey').value);
    formData.append('openai_api_key', document.getElementById('openaiApiKey').value);
    formData.append('personality', document.getElementById('personality').value);
    formData.append('openai_model', document.getElementById('openaiModel').value); // Adicionado
    formData.append('output_path', document.getElementById('outputPath').value);
    formData.append('text_content', document.getElementById('textContent').value);
    appendLog('Campos principais coletados.');

    // Adicionar arquivos
    const files = document.getElementById('files').files;
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    if (files.length) {
        appendLog(`Anexados ${files.length} arquivo(s) de referência.`);
    } else {
        appendLog('Nenhum arquivo adicional foi anexado.');
    }

    const metaBackendUrl = document.querySelector('meta[name="backend-url"]');
    const currentOrigin = (window.location && window.location.origin && window.location.origin !== 'null' && !window.location.origin.startsWith('file://'))
        ? window.location.origin
        : '';

    // Prioridade: Meta tag > Origem atual > Localhost
    const candidates = [
        typeof window !== 'undefined' ? (window.BACKEND_URL || window.backendUrl || '') : '',
        metaBackendUrl ? metaBackendUrl.content.trim() : '',
        currentOrigin
    ].filter(Boolean);

    const backendBaseUrl = (candidates[0] || 'http://localhost:5001').replace(/\/+$/, '');
    const endpoint = `${backendBaseUrl}/generate_ebook`;
    appendLog(`Enviando requisição para ${endpoint}.`);

    try {
        console.info('Enviando requisicao para', endpoint);
        startHeartbeat();
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let errorMessage = 'Erro ao gerar ebook';
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch {
                errorMessage = `${errorMessage}. HTTP ${response.status}`;
            }
            appendLog(`Backend respondeu com erro: ${errorMessage}.`);
            throw new Error(errorMessage);
        }

        const blob = await response.blob();
        stopHeartbeat();
        appendLog('Resposta recebida. Montando arquivo para download.');
        const url = window.URL.createObjectURL(blob);
        const disposition = response.headers.get('Content-Disposition') || '';
        let filename = 'ebook_gerado.pdf';

        const filenameRegex = /filename\*=UTF-8''([^;]+)|filename="?([^\";]+)"?/i;
        const match = disposition.match(filenameRegex);
        if (match) {
            try {
                filename = decodeURIComponent(match[1] || match[2] || filename);
            } catch (_) {
                filename = match[1] || match[2] || filename;
            }
        }

        const downloadLink = document.getElementById('downloadLink');
        downloadLink.href = url;
        downloadLink.download = filename;
        downloadLink.textContent = `Baixar ${filename}`;

        statusDiv.className = 'status success';
        statusDiv.textContent = 'Ebook gerado com sucesso!';
        downloadSection.style.display = 'block';
        appendLog('Processo concluído com sucesso. Link de download disponibilizado.');

        try {
            const tempLink = document.createElement('a');
            tempLink.href = url;
            tempLink.download = filename;
            tempLink.style.display = 'none';
            document.body.appendChild(tempLink);
            tempLink.click();
            document.body.removeChild(tempLink);
        } catch (downloadError) {
            console.warn('Download automático bloqueado:', downloadError);
            appendLog('Download automático bloqueado pelo navegador. Use o botão "Baixar Ebook".');
        }

        setTimeout(() => {
            window.URL.revokeObjectURL(url);
        }, 60 * 1000);
        appendLog('URL temporária será liberada em 60 segundos.');

    } catch (error) {
        stopHeartbeat();
        statusDiv.className = 'status error';
        let hint = '';
        if (error instanceof TypeError) {
            hint = ' Verifique se o backend está acessível, se a URL está correta e se não há bloqueio por CORS.';
        }
        statusDiv.textContent = 'Erro: ' + (error.message || error.toString()) + hint;
        appendLog(`Erro detectado: ${(error.message || error.toString())}${hint}`);
    }
});
