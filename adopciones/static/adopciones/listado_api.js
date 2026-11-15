// Listado de perros compatibles armado en el navegador a partir de la API REST.
(function () {
  const script = document.currentScript;
  const URL_LISTA = script.dataset.urlLista;
  const URL_SOLICITUDES = script.dataset.urlSolicitudes;
  const contenedor = document.getElementById("tarjetas");
  const estado = document.getElementById("estado");
  const buscar = document.getElementById("buscar");
  const minimo = document.getElementById("minimo");
  const valorMinimo = document.getElementById("valor-minimo");
  let perros = [];

  function leerCookie(nombre) {
    const par = document.cookie.split("; ").find(function (c) { return c.startsWith(nombre + "="); });
    return par ? decodeURIComponent(par.split("=")[1]) : "";
  }

  function formatoPorcentaje(n) {
    return n.toLocaleString("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " %";
  }

  function crear(tag, clase, texto) {
    const el = document.createElement(tag);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;      // textContent: no interpreta HTML
    return el;
  }

  function tarjeta(perro) {
    const t = crear("article", "tarjeta");
    t.appendChild(crear("h2", "", perro.nombre));
    t.appendChild(crear("p", "porcentaje", formatoPorcentaje(perro.porcentaje)));
    const barra = crear("div", "barra-porcentaje");
    const relleno = document.createElement("span");
    relleno.style.width = perro.porcentaje + "%";
    barra.appendChild(relleno);
    t.appendChild(barra);
    t.appendChild(crear("p", "datos", perro.edad.toLocaleString("es-AR") + " años · energía " + perro.nivel_energia));
    const boton = crear("button", "boton", "Solicitar adopción");
    boton.type = "button";
    boton.addEventListener("click", function () { solicitar(perro, boton); });
    t.appendChild(boton);
    return t;
  }

  function dibujar() {
    const texto = buscar.value.trim().toLowerCase();
    const min = Number(minimo.value);
    valorMinimo.textContent = min;
    const visibles = perros.filter(function (p) {
      return p.nombre.toLowerCase().includes(texto) && p.porcentaje >= min;
    });
    contenedor.replaceChildren.apply(contenedor, visibles.map(tarjeta));
    estado.textContent = visibles.length ? "" : "Ningún perro coincide con el filtro.";
  }

  async function cargar() {
    try {
      const respuesta = await fetch(URL_LISTA, { headers: { Accept: "application/json" } });
      if (respuesta.status === 401) { window.location.href = script.dataset.urlIngresar; return; }
      if (respuesta.status === 409) { window.location.href = script.dataset.urlPerfil; return; }
      if (!respuesta.ok) throw new Error("Error " + respuesta.status);
      perros = await respuesta.json();
      dibujar();
    } catch (error) {
      estado.textContent = "No se pudo cargar el listado. Probá de nuevo más tarde.";
    }
  }

  async function solicitar(perro, boton) {
    boton.disabled = true;
    try {
      const respuesta = await fetch(URL_SOLICITUDES, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": leerCookie("csrftoken") },
        body: JSON.stringify({ perro: perro.id }),
      });
      if (respuesta.status === 201) {
        boton.textContent = "Solicitud enviada ✓";
      } else {
        const datos = await respuesta.json().catch(function () { return {}; });
        boton.disabled = false;
        estado.textContent = datos.detalle || "No se pudo enviar la solicitud.";
      }
    } catch (error) {
      boton.disabled = false;
      estado.textContent = "No se pudo enviar la solicitud.";
    }
  }

  buscar.addEventListener("input", dibujar);
  minimo.addEventListener("input", dibujar);
  cargar();
})();
