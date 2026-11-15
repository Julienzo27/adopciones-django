// Filtra las tarjetas del listado por nombre y por compatibilidad mínima (sin recargar la página).
(function () {
  const buscar = document.getElementById("buscar");
  const minimo = document.getElementById("minimo");
  const valor = document.getElementById("valor-minimo");
  const tarjetas = Array.from(document.querySelectorAll(".tarjeta"));
  const vacio = document.getElementById("sin-resultados");
  if (!buscar || !minimo) return;

  function filtrar() {
    const texto = buscar.value.trim().toLowerCase();
    const min = Number(minimo.value);
    valor.textContent = min;
    let visibles = 0;
    tarjetas.forEach(function (t) {
      const coincide = t.dataset.nombre.includes(texto) && Number(t.dataset.porcentaje) >= min;
      t.hidden = !coincide;
      if (coincide) visibles += 1;
    });
    vacio.hidden = visibles !== 0 || tarjetas.length === 0;
  }
  buscar.addEventListener("input", filtrar);
  minimo.addEventListener("input", filtrar);
})();
