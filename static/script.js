// ======== Sistema de Controle de Chromebooks ========

// 🟢 Auto-focus no primeiro campo dos formulários
document.addEventListener("DOMContentLoaded", function () {
  const firstInput = document.querySelector(
    "form input[type='text'], form input[type='number'], form input[type='password']"
  );
  if (firstInput) firstInput.focus();
});

// 🟠 Confirmação para ações importantes
function confirmarAcao(mensagem) {
  return confirm(mensagem);
}

// 🔵 Validação de formulários (IGNORA o de empréstimo e o de login)
document.addEventListener("DOMContentLoaded", function () {
  const forms = document.querySelectorAll("form:not(#login-form):not(#emprestimoForm)");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      const requiredFields = form.querySelectorAll("[required]");
      let valid = true;

      requiredFields.forEach((field) => {
        if (!field.value.trim()) {
          valid = false;
          field.classList.add("is-invalid");
        } else {
          field.classList.remove("is-invalid");
        }
      });

      if (!valid) {
        e.preventDefault();
        alert("Por favor, preencha todos os campos obrigatórios.");
      }
    });
  });
});

// 🟣 Feedback visual nos botões de envio
document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll("button[type='submit']");

  buttons.forEach((button) => {
    button.addEventListener("click", function () {
      const form = button.closest("form");

      // Evita travar o botão do formulário de empréstimo (ele já tem seu próprio loading)
      if (form && form.id === "emprestimoForm") return;

      const originalText = button.innerHTML;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';
      button.disabled = true;

      // Restaura automaticamente após 3s (caso falhe)
      setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
      }, 3000);
    });
  });
});

// ======================================================
// 🧩 Devolução — carregar Chromebooks emprestados
// ======================================================
async function carregarEmprestados() {
  const lista = document.getElementById("lista-emprestados");
  if (!lista) return;

  lista.innerHTML =
    "<div class='text-center text-muted py-3'>🔄 Carregando Chromebooks emprestados...</div>";

  try {
    // Timeout para evitar travamento se o servidor demorar
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const resposta = await fetch("/api/chromebooks_emprestados", {
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!resposta.ok) throw new Error("Falha ao buscar dados");

    const dados = await resposta.json();
    lista.innerHTML = "";

    if (!Array.isArray(dados) || dados.length === 0) {
      lista.innerHTML =
        "<div class='alert alert-info text-center'>📭 Nenhum Chromebook emprestado no momento.</div>";
      return;
    }

    dados.forEach((cb) => {
      lista.innerHTML += `
        <div class="card p-3 mb-2 shadow-sm border-start border-primary border-3">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <h6 class="mb-1">💻 Chromebook <b>${cb.numero}</b> — <span class="text-secondary">${cb.carrinho}</span></h6>
              <small class="text-muted">👤 <b>${cb.aluno}</b> - Turma: ${cb.turma || 'N/A'}</small>
            </div>
            <form method="POST" action="/devolucao" onsubmit="return confirmarAcao('Confirmar devolução de ${cb.numero}?')">
              <input type="hidden" name="numero_chromebook" value="${cb.numero}">
              <input type="hidden" name="carrinho" value="${cb.carrinho}">
              <button type="submit" class="btn btn-sm btn-success">
                <i class="bi bi-arrow-return-left"></i> Devolver
              </button>
            </form>
          </div>
        </div>
      `;
    });
  } catch (erro) {
    console.error("Erro ao carregar Chromebooks emprestados:", erro);
    lista.innerHTML =
      "<div class='alert alert-danger text-center'>❌ Erro ao carregar dados. Verifique a conexão.</div>";
  }
}

document.addEventListener("DOMContentLoaded", carregarEmprestados);
