// Mensaje de consola al cargar
console.log("Carrusel y página cargados correctamente.");

// Opcional: Podrías agregar una pausa automática en el carrusel después de unos segundos
const carouselElement = document.querySelector('#carouselExampleIndicators');
const carouselInstance = new bootstrap.Carousel(carouselElement, {
  interval: 3000,  // Cambiar automáticamente cada 3 segundos
  wrap: true
});

