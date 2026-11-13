import * as THREE from './vendor/three.module.min.js';
import { OrbitControls } from './vendor/jsm/controls/OrbitControls.js';

const COR = { ok: 0x73bf69, atencao: 0xff9830, alerta: 0xf2495c, neutro: 0x6e7681, agua: 0x5ea8e6, info: 0x5794f2 };
const P = { piso: 0x353a43, parede: 0x2b2f37, rack: 0x2a2e35, rackLateral: 0x343941, equipamento: 0x3b4149, frente: 0x454c56, contorno: 0x0d0f12, metal: 0x8b93a0 };

const RACK = { x: 0.35, z: -2.15, largura: 0.66, altura: 2.05, profundidade: 1.0 };
const U = 0.0445;
const BASE_U = 0.09;
const FRENTE = RACK.z + RACK.profundidade / 2 - 0.05;
const MAX_SERVIDORES = 10;

export function criarCena(caixa) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x15181d, 1);
  caixa.appendChild(renderer.domElement);

  const cena = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  const VISTA = { alvo: new THREE.Vector3(-0.9, 0.85, -1.3), direcao: new THREE.Vector3(0.55, 0.72, 1).normalize(), zoom: 1 };
  camera.position.copy(VISTA.alvo.clone().add(VISTA.direcao.clone().multiplyScalar(22)));

  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.copy(VISTA.alvo);
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;
  controles.enablePan = true;
  controles.screenSpacePanning = true;
  controles.minZoom = 0.6;
  controles.maxZoom = 4;
  controles.minPolarAngle = 0.2;
  controles.maxPolarAngle = 1.4;
  controles.minAzimuthAngle = -0.5;
  controles.maxAzimuthAngle = 1.7;
  controles.update();

  const luzCeu = new THREE.HemisphereLight(0xf1f5f9, 0x23272e, 1.8);
  cena.add(luzCeu);
  const luzPrincipal = new THREE.DirectionalLight(0xffffff, 1.6);
  luzPrincipal.position.set(-3, 9, 5);
  luzPrincipal.castShadow = true;
  luzPrincipal.shadow.mapSize.set(2048, 2048);
  Object.assign(luzPrincipal.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7 });
  luzPrincipal.shadow.bias = -0.0004;
  cena.add(luzPrincipal);
  const luzEmergencia = new THREE.PointLight(COR.alerta, 0, 10, 1.3);
  luzEmergencia.position.set(-0.5, 2.8, -1.4);
  cena.add(luzEmergencia);

  const mat = (cor, extra = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.85, metalness: 0.05, ...extra });
  const led = (cor, intensidade = 1.6) => mat(cor, { emissive: cor, emissiveIntensity: intensidade, roughness: 0.5 });
  const matContorno = new THREE.LineBasicMaterial({ color: P.contorno, transparent: true, opacity: 0.55 });

  const bloco = (l, a, p, material, x, y, z, pai = cena, contorno = true) => {
    const geo = new THREE.BoxGeometry(l, a, p);
    const m = new THREE.Mesh(geo, material);
    m.position.set(x, y, z);
    m.castShadow = true;
    m.receiveShadow = true;
    if (contorno) m.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), matContorno));
    pai.add(m);
    return m;
  };
  const pequeno = (l, a, p, material, x, y, z, pai = cena) => {
    const m = bloco(l, a, p, material, x, y, z, pai, false);
    m.castShadow = false;
    return m;
  };

  // Sala
  bloco(8, 0.1, 6, mat(P.piso), 0, -0.05, 0, cena, false);
  const juntas = new THREE.GridHelper(8, 13, P.piso, P.piso);
  juntas.scale.z = 6 / 8;
  juntas.position.y = 0.002;
  cena.add(juntas);
  bloco(8.1, 3, 0.1, mat(P.parede), -0.05, 1.5, -3.05);
  bloco(0.1, 3, 6, mat(P.parede), -4.05, 1.5, 0);
  bloco(0.1, 3, 6, mat(P.parede), 4.05, 1.5, 0);

  // Rack
  const rack = new THREE.Group();
  cena.add(rack);
  const { x: rx, z: rz, largura: rl, altura: ra, profundidade: rp } = RACK;
  const matRack = mat(P.rack, { metalness: 0.3, roughness: 0.6 });
  bloco(rl, 0.05, rp, matRack, rx, ra - 0.025, rz, rack);
  bloco(rl, 0.06, rp, matRack, rx, 0.03, rz, rack);
  bloco(0.02, ra - 0.11, rp, mat(P.rackLateral, { metalness: 0.3, roughness: 0.55 }), rx - rl / 2 + 0.01, ra / 2, rz, rack);
  bloco(0.02, ra - 0.11, rp, mat(P.rackLateral, { metalness: 0.3, roughness: 0.55 }), rx + rl / 2 - 0.01, ra / 2, rz, rack);
  bloco(rl - 0.04, ra - 0.11, 0.02, matRack, rx, ra / 2, rz - rp / 2 + 0.01, rack);

  const yDoU = (u, alturaU) => BASE_U + (u - 1) * U + (alturaU * U) / 2;
  const LARG = 0.5, PROF = 0.78;

  const visorUps = criarVisor(256, 64);
  bloco(LARG, 3 * U - 0.004, PROF, mat(0x272b31), rx, yDoU(1, 3), FRENTE - PROF / 2, rack);
  const visor = new THREE.Mesh(new THREE.PlaneGeometry(0.15, 0.038), new THREE.MeshBasicMaterial({ map: visorUps.textura, toneMapped: false }));
  visor.position.set(rx - 0.12, yDoU(1, 3) + 0.01, FRENTE + 0.004);
  rack.add(visor);
  const matLedUps = led(COR.ok);
  pequeno(0.012, 0.012, 0.004, matLedUps, rx + 0.16, yDoU(1, 3) + 0.03, FRENTE + 0.004, rack);

  const servidores3d = [];
  let assinaturaRack = '';
  function montarServidores(lista) {
    const assinatura = lista.map((s) => s.id).join(',');
    if (assinatura === assinaturaRack) return;
    assinaturaRack = assinatura;
    for (const s of servidores3d) rack.remove(s.grupo);
    servidores3d.length = 0;
    lista.slice(0, MAX_SERVIDORES).forEach((srv, i) => {
      const grupo = new THREE.Group();
      grupo.position.set(rx, yDoU(37 - i * 2, 2), 0);
      bloco(LARG, 2 * U - 0.004, PROF, mat(P.frente, { metalness: 0.3, roughness: 0.5 }), 0, 0, FRENTE - PROF / 2, grupo);
      const matEstado = led(COR.ok, 1.8);
      pequeno(0.012, 0.012, 0.004, matEstado, LARG / 2 - 0.03, 0.018, FRENTE + 0.006, grupo);
      rack.add(grupo);
      servidores3d.push({ id: srv.id, grupo, matEstado });
    });
  }

  const tomada = new THREE.Group();
  tomada.position.set(-0.6, 0.42, -2.98);
  bloco(0.15, 0.22, 0.025, mat(0xd6d3cc), 0, 0, 0, tomada);
  const matTomada = led(COR.ok, 1.2);
  pequeno(0.02, 0.02, 0.01, matTomada, 0.045, 0.07, 0.016, tomada);
  cena.add(tomada);

  const curvaCabo = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.6, 0.32, -2.96),
    new THREE.Vector3(-0.58, 0.03, -2.86),
    new THREE.Vector3(-0.3, 0.03, -2.66),
    new THREE.Vector3(rx - 0.15, 0.03, RACK.z - 0.2),
    new THREE.Vector3(rx - 0.15, 0.1, RACK.z + 0.1),
  ]);
  cena.add(new THREE.Mesh(new THREE.TubeGeometry(curvaCabo, 48, 0.012, 8, false), mat(0x121418)));

  const matPulso = new THREE.MeshBasicMaterial({ color: COR.ok, transparent: true, opacity: 0, depthWrite: false });
  const pulsos = [0, 1/3, 2/3].map((fase) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.016, 10, 8), matPulso.clone());
    m.userData.fase = fase;
    cena.add(m);
    return m;
  });

  const ar = new THREE.Group();
  ar.position.set(-2.15, 2.5, -2.84);
  bloco(1.5, 0.38, 0.28, mat(0xd9d8d2, { roughness: 0.6 }), 0, 0, 0, ar);
  pequeno(1.3, 0.035, 0.01, mat(0x2a2d33), 0, -0.13, 0.145, ar);
  cena.add(ar);

  const POCA = new THREE.Vector3(-2.15, 0.006, -2.2);
  const poca = new THREE.Mesh(new THREE.CircleGeometry(0.85, 40), new THREE.MeshStandardMaterial({ color: COR.agua, transparent: true, opacity: 0.55, roughness: 0.1, metalness: 0.2 }));
  poca.rotation.x = -Math.PI / 2;
  poca.position.copy(POCA);
  poca.scale.setScalar(0.001);
  cena.add(poca);
  const gotas = [];
  const geoGota = new THREE.SphereGeometry(0.022, 8, 8);
  geoGota.scale(1, 1.6, 1);
  const matGota = mat(COR.agua, { roughness: 0.1 });
  for (let i = 0; i < 4; i++) {
    const g = new THREE.Mesh(geoGota, matGota);
    g.visible = false;
    g.userData = { fase: i / 4, dx: (i - 1.5) * 0.18 };
    cena.add(g);
    gotas.push(g);
  }

  const dobradica = new THREE.Group();
  dobradica.position.set(-3.98, 0, -1.88);
  bloco(0.045, 2.08, 0.96, mat(0x4a4f57, { roughness: 0.6 }), 0, 1.04, 0.48, dobradica);
  bloco(0.05, 0.03, 0.12, mat(P.metal, { metalness: 0.8, roughness: 0.3 }), 0.04, 1.0, 0.82, dobradica);
  cena.add(dobradica);
  const matBatente = mat(0x3a3f47);
  bloco(0.05, 0.05, 1.06, matBatente, -3.97, 2.1, -1.4);
  bloco(0.05, 2.1, 0.05, matBatente, -3.97, 1.05, -1.91);
  bloco(0.05, 2.1, 0.05, matBatente, -3.97, 1.05, -0.89);

  const sensor = new THREE.Group();
  sensor.position.set(-1.15, 1.45, -2.97);
  bloco(0.16, 0.22, 0.06, mat(0xd6d3cc, { roughness: 0.7 }), 0, 0, 0, sensor);
  const matLedSensor = led(COR.info, 1.4);
  pequeno(0.012, 0.012, 0.008, matLedSensor, -0.05, 0.08, 0.032, sensor);
  const telaSensor = criarVisor(256, 128);
  const tela = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 0.06), new THREE.MeshBasicMaterial({ map: telaSensor.textura, toneMapped: false }));
  tela.position.set(0, -0.02, 0.031);
  sensor.add(tela);
  cena.add(sensor);

  const giroflex = new THREE.Group();
  giroflex.position.set(rx + 0.2, ra, rz + 0.25);
  giroflex.visible = false;
  const matGiroflex = mat(0x5a2a2e, { emissive: COR.alerta, emissiveIntensity: 0, roughness: 0.4 });
  giroflex.add(new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.025, 20), mat(0x2a2e35)));
  const cupula = new THREE.Mesh(new THREE.SphereGeometry(0.04, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), matGiroflex);
  cupula.position.y = 0.025;
  giroflex.add(cupula);
  cena.add(giroflex);

  const alvo = { porta: 0, poca: 0.001, agua: false, emergencia: false, energiaOk: false, giroflex: 0, corGiroflex: COR.alerta, online: true, alertaSensor: false };

  function atualizar(r) {
    const amb = r.ambiente;
    const on = amb.online;
    montarServidores(r.servidores);
    for (const s of servidores3d) pintar(s.matEstado, COR.ok);
    const semEnergia = on && amb.energia === 0;
    pintar(matTomada, semEnergia ? COR.alerta : COR.ok);
    pintar(matLedUps, semEnergia ? COR.atencao : COR.ok);
    alvo.emergencia = semEnergia;
    alvo.energiaOk = on && amb.energia === 1;
    visorUps.escrever(!on || amb.energia === null ? ['UPS', 'ENTRADA --', '#8b949e'] : semEnergia ? ['UPS', 'ENTRADA FALHA', '#ff9830'] : ['UPS', 'ENTRADA OK', '#9fd89a']);
    alvo.agua = on && amb.agua === 1;
    alvo.poca = alvo.agua ? 1 : 0.001;
    const aberta = on && amb.porta === 1;
    alvo.porta = aberta ? 1.2 : 0;
    matBatente.color.set(aberta ? COR.alerta : 0x3a3f47);
    const t = on ? amb.temperatura : null;
    telaSensor.escrever(t === null ? ['--.-', on ? 'DHT?' : 'OFF', '#8b949e'] : [`${t.toFixed(1)}°`, `${amb.umidade ?? '--'}%`, '#d7dbe0'], true);
    pintar(matLedSensor, on ? COR.info : COR.alerta);
    alvo.online = on;
    alvo.alertaSensor = alvo.agua || aberta || semEnergia;
  }

  const relogio = new THREE.Clock();
  let quadro = 0;
  const vida = { viva: true };

  function animar() {
    if (!caixa.isConnected) { destruir(); return; }
    quadro = requestAnimationFrame(animar);
    const dt = Math.min(relogio.getDelta(), 0.1);
    const t = relogio.elapsedTime;
    const suave = (a, b, v) => a + (b - a) * Math.min(1, dt * v);

    dobradica.rotation.y = suave(dobradica.rotation.y, alvo.porta, 3);
    const s = suave(poca.scale.x, alvo.poca, alvo.agua ? 0.6 : 2);
    poca.scale.setScalar(s);
    poca.visible = s > 0.01;

    for (const g of gotas) {
      g.visible = alvo.agua;
      if (!g.visible) continue;
      const q = (t * 0.6 + g.userData.fase) % 1;
      g.position.set(ar.position.x + g.userData.dx, 2.3 * (1 - q * q), ar.position.z + 0.25);
    }

    const fator = alvo.emergencia ? 0.35 : 1;
    luzPrincipal.intensity = suave(luzPrincipal.intensity, 1.6 * fator, 2);
    luzCeu.intensity = suave(luzCeu.intensity, 1.8 * (alvo.emergencia ? 0.4 : 1), 2);
    luzEmergencia.intensity = alvo.emergencia ? 10 + 8 * Math.sin(t * 4) : suave(luzEmergencia.intensity, 0, 4);

    giroflex.visible = !!alvo.giroflex;
    const grave = alvo.corGiroflex === COR.alerta;
    giroflex.rotation.y += dt * (grave ? 5 : 2.5);
    matGiroflex.emissive.setHex(alvo.corGiroflex);
    matGiroflex.emissiveIntensity = alvo.giroflex ? 1.5 + Math.sin(t * (grave ? 10 : 5)) : 0;

    matLedSensor.emissiveIntensity = !alvo.online ? 0 : alvo.alertaSensor ? (Math.floor(t * 8) % 2 ? 1.8 : 0.2) : 1.4;

    controles.update();
    renderer.render(cena, camera);
  }

  function redimensionar() {
    const w = Math.max(200, caixa.clientWidth);
    const h = Math.max(200, caixa.clientHeight);
    renderer.setSize(w, h);
    const aspecto = w / h;
    const alturaVista = 6.4;
    camera.top = alturaVista / 2;
    camera.bottom = -alturaVista / 2;
    camera.left = (-alturaVista * aspecto) / 2;
    camera.right = (alturaVista * aspecto) / 2;
    VISTA.zoom = aspecto < 1.5 ? 0.85 * (aspecto / 1.5) + 0.15 : 1;
    camera.zoom = VISTA.zoom;
    camera.updateProjectionMatrix();
  }

  function destruir() {
    vida.viva = false;
    cancelAnimationFrame(quadro);
    observador.disconnect();
    controles.dispose();
    cena.traverse((o) => {
      o.geometry?.dispose?.();
      if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.map?.dispose(); m.dispose(); });
    });
    renderer.dispose();
  }

  const observador = new ResizeObserver(redimensionar);
  observador.observe(caixa);
  redimensionar();
  animar();

  return Object.assign(vida, { atualizar, destruir });
}

function pintar(material, cor) {
  material.color.set(cor);
  if (material.emissive) material.emissive.set(cor);
}

function texturaCanvas(w, h, desenhar) {
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h;
  desenhar(canvas.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(canvas);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function pintarCanvas(textura, desenhar) {
  const c = textura.image.getContext('2d');
  c.clearRect(0, 0, textura.image.width, textura.image.height);
  desenhar(c, textura.image.width, textura.image.height);
  textura.needsUpdate = true;
}

function criarVisor(w, h) {
  const textura = texturaCanvas(w, h, (c) => { c.fillStyle = '#0e1114'; c.fillRect(0, 0, w, h); });
  let anterior = '';
  return {
    textura,
    escrever([l1, l2, cor], grande = false) {
      const chave = l1 + l2 + cor;
      if (chave === anterior) return;
      anterior = chave;
      pintarCanvas(textura, (c) => {
        c.fillStyle = '#0e1114'; c.fillRect(0, 0, w, h);
        c.fillStyle = cor; c.textBaseline = 'middle';
        c.font = `${grande ? 'bold ' : ''}${Math.round(h * (grande ? 0.42 : 0.32))}px Consolas, monospace`;
        c.fillText(l1, 10, h * (grande ? 0.34 : 0.32));
        c.font = `${Math.round(h * (grande ? 0.24 : 0.32))}px Consolas, monospace`;
        c.fillText(l2, 10, h * (grande ? 0.76 : 0.72));
      });
    },
  };
}
