/* Névora Moda! — mejoras progresivas. Todo funciona también sin JavaScript. */
(function () {
  "use strict";

  // Confirmación solo para acciones destructivas (eliminar, cancelar, cerrar sesión).
  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) event.preventDefault();
  }, true);

  // Indicador de carga: evita envíos dobles y avisa que la acción está en curso.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches("form[data-loading]") || event.defaultPrevented) return;
    var button = form.querySelector("button[type=submit]");
    if (!button || button.dataset.busy) return;
    button.dataset.busy = "1";
    button.setAttribute("aria-busy", "true");
    button.innerHTML = '<span class="spinner-border" role="status" aria-hidden="true"></span> ' +
      (form.dataset.loading || "Procesando...");
    window.setTimeout(function () { button.disabled = true; }, 0);
  });

  document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () { select.form.submit(); });
  });

  // Pago: los datos de tarjeta solo se muestran para métodos con tarjeta.
  var method = document.getElementById("payment_method");
  var cardFields = document.getElementById("card-fields");
  if (method && cardFields) {
    var cardMethods = (cardFields.dataset.cardMethods || "").split(",");
    var toggle = function () {
      var show = cardMethods.indexOf(method.value) !== -1;
      cardFields.hidden = !show;
      var cash = document.getElementById("cash-note");
      if (cash) cash.hidden = show || !method.value;
    };
    method.addEventListener("change", toggle);
    toggle();
  }
})();
