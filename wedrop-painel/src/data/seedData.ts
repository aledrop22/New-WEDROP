import { CategoryRecord, ProductRecord, StockEventRecord } from '../types/wedrop';
import { getLocalDateString } from '../utils/status';

export const INITIAL_CATEGORIES: CategoryRecord[] = [
  { category_url: 'https://wedrop.com.br/categoria/cozinha', name: 'Cozinha', expected_products: 48, mapped_products: 48, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/organizacao', name: 'Organização', expected_products: 42, mapped_products: 42, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/limpeza-e-lavanderia', name: 'Limpeza e Lavanderia', expected_products: 36, mapped_products: 36, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/banheiro', name: 'Banheiro', expected_products: 29, mapped_products: 29, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/decoracao-e-texteis', name: 'Decoração e Têxteis', expected_products: 35, mapped_products: 35, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/eletroportateis', name: 'Eletroportáteis', expected_products: 24, mapped_products: 24, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/brinquedos', name: 'Brinquedos', expected_products: 32, mapped_products: 32, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/papelaria-e-escritorio', name: 'Papelaria e Escritório', expected_products: 28, mapped_products: 28, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/ferramentas-e-automotivo', name: 'Ferramentas e Automotivo', expected_products: 30, mapped_products: 30, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/esporte-e-lazer', name: 'Esporte e Lazer', expected_products: 25, mapped_products: 25, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/pets', name: 'Pets', expected_products: 34, mapped_products: 34, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/beleza-e-cuidado-pessoal', name: 'Beleza e Cuidado Pessoal', expected_products: 38, mapped_products: 38, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/moda-malas-e-acessorios', name: 'Moda, Malas e Acessórios', expected_products: 26, mapped_products: 26, updated_at: new Date().toISOString() },
  { category_url: 'https://wedrop.com.br/categoria/natal-e-festas', name: 'Natal e Festas', expected_products: 20, mapped_products: 20, updated_at: new Date().toISOString() },
];

// Curated realistic products across categories with previous price and historical status
export const INITIAL_PRODUCTS: ProductRecord[] = [
  // Cozinha
  {
    product_id: 'prod-coz-001',
    name: 'Kit 5 Utensílios de Cozinha em Silicone com Cabo de Madeira Bambu',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/kit-5-utensilios-silicone-bambu',
    sku: 'WD-COZ-501',
    ean: '7898512401012',
    price: 'R$ 49,90',
    previous_price: 'R$ 54,90', // Baixou
    availability: 'Disponível',
    stock: '142',
    total_stock_count: '150',
    real_balance: '142',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Utilidades Gourmet Brasil',
    cnpj: '12.345.678/0001-90',
    origin_state: 'SP',
    ncm: '3924.10.00',
    weight: '0.450',
    height: '32.0',
    width: '10.0',
    length: '10.0',
    description: 'Conjunto premium com espátula, concha, colher vazada e pegador.',
    number_sales: '320',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-coz-002',
    name: 'Triturador e Processador Manual de Alimentos 3 Lâminas Inox 500ml',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/triturador-processador-manual-500ml',
    sku: 'WD-COZ-502',
    ean: '7898512401029',
    price: 'R$ 24,90',
    previous_price: 'R$ 21,90', // Subiu
    availability: 'Disponível',
    stock: '380',
    total_stock_count: '400',
    real_balance: '380',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Pratic Lar Importações',
    cnpj: '23.456.789/0001-01',
    origin_state: 'SC',
    ncm: '8205.51.00',
    weight: '0.240',
    height: '13.0',
    width: '13.0',
    length: '10.0',
    description: 'Processador manual com acionamento por corda retrátil rápida.',
    number_sales: '580',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-coz-003',
    name: 'Garrafa Térmica Inox Vacuum 500ml com Sensor Digital LED',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/garrafa-termica-digital-led-500ml',
    sku: 'WD-COZ-503',
    ean: '7898512401036',
    price: 'R$ 38,50',
    previous_price: 'R$ 38,50', // Estável
    availability: 'Disponível',
    stock: '85',
    total_stock_count: '90',
    real_balance: '85',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'InoxTech Suprimentos',
    cnpj: '34.567.890/0001-12',
    origin_state: 'PR',
    ncm: '9617.00.10',
    weight: '0.310',
    height: '24.0',
    width: '7.0',
    length: '7.0',
    description: 'Mantém bebidas quentes ou frias por até 12 horas.',
    number_sales: '410',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-coz-004',
    name: 'Cortador e Fatiador de Legumes Mandoline Multifuncional 6 Peças',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/fatiador-mandoline-multifuncional',
    sku: 'WD-COZ-504',
    ean: '7898512401043',
    price: 'R$ 32,90',
    previous_price: 'R$ 37,90', // Baixou
    availability: 'Indisponível',
    stock: '0',
    total_stock_count: '0',
    real_balance: '0',
    is_active: 'Inativo',
    was_active_yesterday: true, // Esgotou nas últimas 24h
    supplier: 'Pratic Lar Importações',
    cnpj: '23.456.789/0001-01',
    origin_state: 'SC',
    ncm: '8205.51.00',
    weight: '0.380',
    height: '11.0',
    width: '12.0',
    length: '28.0',
    description: 'Mandoline com protetor de mãos e lâminas de corte reguláveis.',
    number_sales: '210',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-coz-005',
    name: 'Forma de Silicone para Air Fryer Reutilizável Antiaderente 20cm',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/forma-silicone-air-fryer-20cm',
    sku: 'WD-COZ-505',
    ean: '7898512401050',
    price: 'R$ 18,90',
    previous_price: 'R$ 15,90', // Subiu
    availability: 'Disponível',
    stock: '520',
    total_stock_count: '550',
    real_balance: '520',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Utilidades Gourmet Brasil',
    cnpj: '12.345.678/0001-90',
    origin_state: 'SP',
    ncm: '3924.10.00',
    weight: '0.120',
    height: '6.0',
    width: '20.0',
    length: '20.0',
    description: 'Silicone alimentício atóxico resistente até 230°C.',
    number_sales: '940',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-coz-006',
    name: 'Dispenser Dosador de Azeite e Vinagre em Vidro com Bico Inox',
    category: 'Cozinha',
    url: 'https://wedrop.com.br/produto/dispenser-azeite-vidro-bico-inox',
    sku: 'WD-COZ-506',
    ean: '7898512401067',
    price: 'R$ 22,00',
    previous_price: 'R$ 22,00',
    availability: '',
    stock: '78',
    total_stock_count: '80',
    real_balance: '78',
    is_active: '', // Sem status
    was_active_yesterday: false,
    supplier: 'Utilidades Gourmet Brasil',
    cnpj: '12.345.678/0001-90',
    origin_state: 'SP',
    ncm: '7013.49.00',
    weight: '0.280',
    height: '25.0',
    width: '6.0',
    length: '6.0',
    description: 'Vidro borossilicato com bico retrátil corta-gotas.',
    number_sales: '115',
    updated_at: new Date().toISOString()
  },

  // Organização
  {
    product_id: 'prod-org-001',
    name: 'Kit 6 Organizadores de Gaveta Acrílico Empilháveis Diamond',
    category: 'Organização',
    url: 'https://wedrop.com.br/produto/kit-6-organizadores-acrilico-diamond',
    sku: 'WD-ORG-601',
    ean: '7898512402019',
    price: 'R$ 54,90',
    previous_price: 'R$ 59,90', // Baixou
    availability: 'Disponível',
    stock: '210',
    total_stock_count: '220',
    real_balance: '210',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Organize Já Plásticos',
    cnpj: '45.678.901/0001-23',
    origin_state: 'SP',
    ncm: '3924.90.00',
    weight: '0.620',
    height: '15.0',
    width: '20.0',
    length: '30.0',
    description: 'Caixas organizadoras transparentes modulares para roupas e maquiagem.',
    number_sales: '430',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-org-002',
    name: 'Suporte Cabideiro Multiuso para Calças 5 em 1 Inox Antideslizante',
    category: 'Organização',
    url: 'https://wedrop.com.br/produto/cabideiro-calcas-5-em-1-inox',
    sku: 'WD-ORG-602',
    ean: '7898512402026',
    price: 'R$ 29,90',
    previous_price: 'R$ 29,90',
    availability: 'Disponível',
    stock: '340',
    total_stock_count: '350',
    real_balance: '340',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Organize Já Plásticos',
    cnpj: '45.678.901/0001-23',
    origin_state: 'SP',
    ncm: '7323.99.00',
    weight: '0.210',
    height: '34.0',
    width: '15.0',
    length: '2.0',
    description: 'Otimiza até 80% do espaço no armário ou closet.',
    number_sales: '670',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-org-003',
    name: 'Kit 4 Caixas Organizadoras com Tampa de Bambu e Travas',
    category: 'Organização',
    url: 'https://wedrop.com.br/produto/kit-caixas-tampa-bambu',
    sku: 'WD-ORG-603',
    ean: '7898512402033',
    price: 'R$ 89,00',
    previous_price: 'R$ 95,00', // Baixou
    availability: 'Indisponível',
    stock: '0',
    total_stock_count: '0',
    real_balance: '0',
    is_active: 'Inativo',
    was_active_yesterday: true, // Esgotou
    supplier: 'Casa & Conforto Ltda',
    cnpj: '56.789.012/0001-34',
    origin_state: 'MG',
    ncm: '4421.99.00',
    weight: '1.200',
    height: '22.0',
    width: '28.0',
    length: '38.0',
    description: 'Design escandinavo com pegadores anatômicos.',
    number_sales: '180',
    updated_at: new Date().toISOString()
  },

  // Limpeza e Lavanderia
  {
    product_id: 'prod-limp-001',
    name: 'Mop Giratório 360 Graus com Balde e 2 Refis de Microfibra',
    category: 'Limpeza e Lavanderia',
    url: 'https://wedrop.com.br/produto/mop-giratorio-360-balde-2-refis',
    sku: 'WD-LMP-701',
    ean: '7898512403016',
    price: 'R$ 69,90',
    previous_price: 'R$ 79,90', // Baixou R$ 10
    availability: 'Disponível',
    stock: '180',
    total_stock_count: '200',
    real_balance: '180',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'CleanMax Soluções',
    cnpj: '67.890.123/0001-45',
    origin_state: 'SP',
    ncm: '9603.90.00',
    weight: '1.450',
    height: '25.0',
    width: '27.0',
    length: '46.0',
    description: 'Cesto centrífuga para secagem rápida sem contato com a água.',
    number_sales: '510',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-limp-002',
    name: 'Kit 10 Panos Mágicos de Microfibra Absorventes Sem Riscar',
    category: 'Limpeza e Lavanderia',
    url: 'https://wedrop.com.br/produto/panos-magicos-microfibra-kit-10',
    sku: 'WD-LMP-702',
    ean: '7898512403023',
    price: 'R$ 19,90',
    previous_price: 'R$ 19,90',
    availability: 'Disponível',
    stock: '420',
    total_stock_count: '450',
    real_balance: '420',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'CleanMax Soluções',
    cnpj: '67.890.123/0001-45',
    origin_state: 'SP',
    ncm: '6307.10.00',
    weight: '0.220',
    height: '5.0',
    width: '30.0',
    length: '30.0',
    description: 'Tecido de alta absorção para vidros, bancadas e automóveis.',
    number_sales: '820',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-limp-003',
    name: 'Escova Elétrica Giratória para Limpeza de Azulejos e Pisos 4 em 1',
    category: 'Limpeza e Lavanderia',
    url: 'https://wedrop.com.br/produto/escova-eletrica-limpeza-4em1',
    sku: 'WD-LMP-703',
    ean: '7898512403030',
    price: 'R$ 84,90',
    previous_price: 'R$ 84,90',
    availability: '',
    stock: '45',
    total_stock_count: '50',
    real_balance: '45',
    is_active: '',
    was_active_yesterday: false,
    supplier: 'CleanMax Soluções',
    cnpj: '67.890.123/0001-45',
    origin_state: 'SP',
    ncm: '8509.80.90',
    weight: '0.680',
    height: '18.0',
    width: '12.0',
    length: '26.0',
    description: 'Motor de alto torque bivolt recarregável via USB.',
    number_sales: '90',
    updated_at: new Date().toISOString()
  },

  // Eletroportáteis
  {
    product_id: 'prod-ele-001',
    name: 'Mini Liquidificador Portátil 6 Lâminas USB Shake 380ml',
    category: 'Eletroportáteis',
    url: 'https://wedrop.com.br/produto/mini-liquidificador-portatil-usb',
    sku: 'WD-ELE-801',
    ean: '7898512404013',
    price: 'R$ 39,90',
    previous_price: 'R$ 44,90', // Baixou R$ 5
    availability: 'Disponível',
    stock: '310',
    total_stock_count: '320',
    real_balance: '310',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'EletroMix Imports',
    cnpj: '78.901.234/0001-56',
    origin_state: 'PR',
    ncm: '8509.40.10',
    weight: '0.410',
    height: '24.0',
    width: '8.5',
    length: '8.5',
    description: 'Bateria interna de 2000mAh para sucos e vitaminas fitness.',
    number_sales: '640',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-ele-002',
    name: 'Seladora a Vácuo Portátil para Alimentos com 10 Sacos Inclusos',
    category: 'Eletroportáteis',
    url: 'https://wedrop.com.br/produto/seladora-vacuo-portatil-alimentos',
    sku: 'WD-ELE-802',
    ean: '7898512404020',
    price: 'R$ 59,90',
    previous_price: 'R$ 52,90', // Subiu R$ 7
    availability: 'Disponível',
    stock: '115',
    total_stock_count: '130',
    real_balance: '115',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'EletroMix Imports',
    cnpj: '78.901.234/0001-56',
    origin_state: 'PR',
    ncm: '8422.30.29',
    weight: '0.590',
    height: '6.0',
    width: '9.0',
    length: '38.0',
    description: 'Conserva os alimentos até 5 vezes mais frescos no freezer.',
    number_sales: '290',
    updated_at: new Date().toISOString()
  },

  // Banheiro
  {
    product_id: 'prod-ban-001',
    name: 'Porta Escova de Dentes Esterilizador UV com Dispenser Pasta',
    category: 'Banheiro',
    url: 'https://wedrop.com.br/produto/porta-escovas-esterilizador-uv',
    sku: 'WD-BAN-101',
    ean: '7898512405010',
    price: 'R$ 45,00',
    previous_price: 'R$ 49,90', // Baixou
    availability: 'Disponível',
    stock: '160',
    total_stock_count: '170',
    real_balance: '160',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Sanitex Metais',
    cnpj: '89.012.345/0001-67',
    origin_state: 'RS',
    ncm: '8539.49.00',
    weight: '0.330',
    height: '12.0',
    width: '6.0',
    length: '20.0',
    description: 'Lâmpada ultravioleta germicida com carregamento USB.',
    number_sales: '380',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-ban-002',
    name: 'Tapete de Banheiro Antiderrapante Diatomita Secagem Instantânea',
    category: 'Banheiro',
    url: 'https://wedrop.com.br/produto/tapete-diatomita-secagem-instantanea',
    sku: 'WD-BAN-102',
    ean: '7898512405027',
    price: 'R$ 39,90',
    previous_price: 'R$ 39,90',
    availability: 'Disponível',
    stock: '250',
    total_stock_count: '260',
    real_balance: '250',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Sanitex Metais',
    cnpj: '89.012.345/0001-67',
    origin_state: 'RS',
    ncm: '5705.00.00',
    weight: '0.450',
    height: '0.4',
    width: '40.0',
    length: '60.0',
    description: 'Pedra de diatomácea macia que absorve umidade em 3 segundos.',
    number_sales: '520',
    updated_at: new Date().toISOString()
  },

  // Decoração e Têxteis
  {
    product_id: 'prod-dec-001',
    name: 'Fita LED RGB 5050 5 Metros com Controle Remoto e Fonte 12V',
    category: 'Decoração e Têxteis',
    url: 'https://wedrop.com.br/produto/fita-led-rgb-5-metros-controle',
    sku: 'WD-DEC-201',
    ean: '7898512406017',
    price: 'R$ 29,90',
    previous_price: 'R$ 26,90', // Subiu
    availability: 'Disponível',
    stock: '380',
    total_stock_count: '400',
    real_balance: '380',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Luz & Decoração Brasil',
    cnpj: '90.123.456/0001-78',
    origin_state: 'SP',
    ncm: '9405.40.90',
    weight: '0.210',
    height: '14.0',
    width: '14.0',
    length: '4.0',
    description: 'Iluminação decorativa com 16 cores e 4 modos de transição.',
    number_sales: '710',
    updated_at: new Date().toISOString()
  },

  // Pets
  {
    product_id: 'prod-pet-001',
    name: 'Fonte Bebedouro para Cães e Gatos Automática Silenciosa 2 Litros',
    category: 'Pets',
    url: 'https://wedrop.com.br/produto/fonte-bebedouro-pet-2-litros',
    sku: 'WD-PET-301',
    ean: '7898512407014',
    price: 'R$ 52,90',
    previous_price: 'R$ 48,00', // Subiu
    availability: 'Disponível',
    stock: '190',
    total_stock_count: '200',
    real_balance: '190',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'PetLife Suprimentos',
    cnpj: '01.234.567/0001-89',
    origin_state: 'SP',
    ncm: '8413.70.80',
    weight: '0.560',
    height: '16.0',
    width: '18.0',
    length: '18.0',
    description: 'Estimula seu pet a beber mais água fresca com sistema triplo.',
    number_sales: '430',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-pet-002',
    name: 'Luva Tira Pelos Magnética Massageadora Nano Escova',
    category: 'Pets',
    url: 'https://wedrop.com.br/produto/luva-tira-pelos-magnetica-pet',
    sku: 'WD-PET-302',
    ean: '7898512407021',
    price: 'R$ 14,90',
    previous_price: 'R$ 12,90', // Subiu
    availability: 'Disponível',
    stock: '480',
    total_stock_count: '500',
    real_balance: '480',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'PetLife Suprimentos',
    cnpj: '01.234.567/0001-89',
    origin_state: 'SP',
    ncm: '3926.90.90',
    weight: '0.080',
    height: '2.0',
    width: '17.0',
    length: '23.0',
    description: 'Ponta de silicone macio que retém até 95% dos pelos mortos.',
    number_sales: '910',
    updated_at: new Date().toISOString()
  },

  // Beleza e Cuidado Pessoal
  {
    product_id: 'prod-bel-001',
    name: 'Escova Secadora e Alisadora Oval 3 em 1 Soft Hair 1200W',
    category: 'Beleza e Cuidado Pessoal',
    url: 'https://wedrop.com.br/produto/escova-secadora-alisadora-1200w',
    sku: 'WD-BEL-401',
    ean: '7898512408011',
    price: 'R$ 79,90',
    previous_price: 'R$ 89,90', // Baixou R$ 10
    availability: 'Disponível',
    stock: '130',
    total_stock_count: '140',
    real_balance: '130',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Glamour Cosméticos',
    cnpj: '11.222.333/0001-44',
    origin_state: 'SP',
    ncm: '8516.31.00',
    weight: '0.620',
    height: '10.0',
    width: '12.0',
    length: '38.0',
    description: 'Cerdas mistas com pontas emborrachadas e ionização.',
    number_sales: '680',
    updated_at: new Date().toISOString()
  },
  {
    product_id: 'prod-bel-002',
    name: 'Modelador de Cachos Automático sem Fio Cerâmica Display LCD',
    category: 'Beleza e Cuidado Pessoal',
    url: 'https://wedrop.com.br/produto/modelador-cachos-automatico-lcd',
    sku: 'WD-BEL-402',
    ean: '7898512408028',
    price: 'R$ 94,00',
    previous_price: 'R$ 99,00', // Baixou
    availability: 'Disponível',
    stock: '80',
    total_stock_count: '90',
    real_balance: '80',
    is_active: 'Ativo',
    was_active_yesterday: false, // Reativado nas últimas 24h!
    supplier: 'Glamour Cosméticos',
    cnpj: '11.222.333/0001-44',
    origin_state: 'SP',
    ncm: '8516.32.00',
    weight: '0.450',
    height: '6.0',
    width: '7.0',
    length: '20.0',
    description: 'Câmara giratória anti-emaranhamento bivolt recarregável.',
    number_sales: '310',
    updated_at: new Date().toISOString()
  },

  // Ferramentas e Automotivo
  {
    product_id: 'prod-fer-001',
    name: 'Compressor de Ar Portátil Digital para Pneus 150 PSI',
    category: 'Ferramentas e Automotivo',
    url: 'https://wedrop.com.br/produto/compressor-ar-portatil-digital-150psi',
    sku: 'WD-FER-901',
    ean: '7898512409018',
    price: 'R$ 119,00',
    previous_price: 'R$ 129,00', // Baixou R$ 10
    availability: 'Disponível',
    stock: '95',
    total_stock_count: '100',
    real_balance: '95',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'AutoForce Equipamentos',
    cnpj: '22.333.444/0001-55',
    origin_state: 'SP',
    ncm: '8414.80.19',
    weight: '0.520',
    height: '14.0',
    width: '8.0',
    length: '5.0',
    description: 'Parada automática na pressão desejada com iluminação LED.',
    number_sales: '490',
    updated_at: new Date().toISOString()
  },

  // Brinquedos
  {
    product_id: 'prod-brin-001',
    name: 'Drone Infantil Quadricóptero com Câmera HD e Sensores',
    category: 'Brinquedos',
    url: 'https://wedrop.com.br/produto/drone-quadricoptero-camera-hd',
    sku: 'WD-BRN-001',
    ean: '7898512410014',
    price: 'R$ 139,00',
    previous_price: 'R$ 139,00',
    availability: 'Disponível',
    stock: '65',
    total_stock_count: '70',
    real_balance: '65',
    is_active: 'Ativo',
    was_active_yesterday: false, // Reativado nas últimas 24h!
    supplier: 'Kids & Toys Import',
    cnpj: '33.444.555/0001-66',
    origin_state: 'PR',
    ncm: '9503.00.99',
    weight: '0.380',
    height: '8.0',
    width: '22.0',
    length: '22.0',
    description: 'Controle 2.4GHz com retorno automático e decolagem rápida.',
    number_sales: '360',
    updated_at: new Date().toISOString()
  },

  // Papelaria e Escritório
  {
    product_id: 'prod-pap-001',
    name: 'Kit Marcadores de Texto Pastel 6 Cores em Estojo',
    category: 'Papelaria e Escritório',
    url: 'https://wedrop.com.br/produto/kit-marcadores-pastel-6-cores',
    sku: 'WD-PAP-101',
    ean: '7898512411011',
    price: 'R$ 18,50',
    previous_price: 'R$ 16,90', // Subiu
    availability: 'Disponível',
    stock: '280',
    total_stock_count: '300',
    real_balance: '280',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Papel & Arte Atacado',
    cnpj: '44.555.666/0001-77',
    origin_state: 'SP',
    ncm: '9608.20.00',
    weight: '0.110',
    height: '2.0',
    width: '8.0',
    length: '15.0',
    description: 'Ponta chanfrada macia para lettering e anotações.',
    number_sales: '490',
    updated_at: new Date().toISOString()
  },

  // Esporte e Lazer
  {
    product_id: 'prod-esp-001',
    name: 'Kit 5 Faixas Elásticas Mini Bands Treino Funcional',
    category: 'Esporte e Lazer',
    url: 'https://wedrop.com.br/produto/kit-mini-bands-treino-funcional',
    sku: 'WD-ESP-201',
    ean: '7898512412018',
    price: 'R$ 22,90',
    previous_price: 'R$ 19,90', // Subiu R$ 3
    availability: 'Disponível',
    stock: '370',
    total_stock_count: '400',
    real_balance: '370',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'FitPro Brasil',
    cnpj: '55.666.777/0001-88',
    origin_state: 'SC',
    ncm: '9506.91.00',
    weight: '0.140',
    height: '3.0',
    width: '10.0',
    length: '18.0',
    description: '5 níveis de resistência progressiva do leve ao pesado.',
    number_sales: '640',
    updated_at: new Date().toISOString()
  },

  // Moda, Malas e Acessórios
  {
    product_id: 'prod-mod-001',
    name: 'Mochila Antifurto Impermeável para Notebook até 15.6 USB',
    category: 'Moda, Malas e Acessórios',
    url: 'https://wedrop.com.br/produto/mochila-antifurto-notebook-usb',
    sku: 'WD-MOD-301',
    ean: '7898512413015',
    price: 'R$ 74,90',
    previous_price: 'R$ 79,90', // Baixou R$ 5
    availability: 'Disponível',
    stock: '150',
    total_stock_count: '160',
    real_balance: '150',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Urban Luggage & Bags',
    cnpj: '66.777.888/0001-99',
    origin_state: 'SP',
    ncm: '4202.92.00',
    weight: '0.780',
    height: '44.0',
    width: '14.0',
    length: '30.0',
    description: 'Zíper oculto contra furto com compartimento acolchoado.',
    number_sales: '420',
    updated_at: new Date().toISOString()
  },

  // Natal e Festas
  {
    product_id: 'prod-nat-001',
    name: 'Cortina de LED Cascata 3x2m 300 Lâmpadas 8 Funções Luz Quente',
    category: 'Natal e Festas',
    url: 'https://wedrop.com.br/produto/cortina-led-cascata-3x2m',
    sku: 'WD-NAT-401',
    ean: '7898512414012',
    price: 'R$ 49,90',
    previous_price: 'R$ 45,00', // Subiu R$ 4,90
    availability: 'Disponível',
    stock: '210',
    total_stock_count: '220',
    real_balance: '210',
    is_active: 'Ativo',
    was_active_yesterday: true,
    supplier: 'Festas & Luz Importadora',
    cnpj: '77.888.999/0001-10',
    origin_state: 'SP',
    ncm: '9405.40.90',
    weight: '0.340',
    height: '10.0',
    width: '12.0',
    length: '16.0',
    description: 'Iluminação decorativa festiva para cortinas e sacadas.',
    number_sales: '390',
    updated_at: new Date().toISOString()
  }
];

// Helper to generate dynamic stock movements for the past 45 days, with realistic last 24h & yesterday events
export function generateInitialStockEvents(products: ProductRecord[]): StockEventRecord[] {
  const events: StockEventRecord[] = [];
  const now = new Date();
  
  products.forEach((product, pIdx) => {
    // Generate sales and stock-ins over past 40 days
    for (let daysAgo = 40; daysAgo >= 0; daysAgo--) {
      const eventDate = new Date(now);
      eventDate.setDate(now.getDate() - daysAgo);
      eventDate.setHours(8 + (pIdx % 12), (pIdx * 7) % 60, 0);
      const dateIso = eventDate.toISOString();
      const dateLocal = getLocalDateString(eventDate);
      
      // For Today (daysAgo === 0) and Yesterday (daysAgo === 1), create pronounced movement for clear 24h comparisons
      if (daysAgo === 0) {
        // Today's sales (last 24 hours)
        // High sales for top items
        const baseQty = (pIdx === 0 || pIdx === 4 || pIdx === 7 || pIdx === 11 || pIdx === 13)
          ? Math.floor(Math.random() * 15) + 18 // 18 - 32 units
          : Math.floor(Math.random() * 10) + 4;  // 4 - 13 units
        
        events.push({
          event_id: `evt-sale-${product.product_id}-today`,
          product_id: product.product_id,
          movement_type: 'SAÍDA - VENDA (24H)',
          event_kind: 'sale',
          quantity: baseQty,
          event_at: dateIso,
          event_at_raw: `${dateLocal} ${eventDate.toLocaleTimeString('pt-BR')}`,
          nf_key: `352610${Math.floor(1000000000 + Math.random() * 9000000000)}`,
          recorded_at: dateIso
        });

        // Some products had restock today!
        if (pIdx === 0 || pIdx === 3 || pIdx === 8 || pIdx === 12) {
          const restockQty = (pIdx === 3) ? 50 : 25;
          events.push({
            event_id: `evt-in-${product.product_id}-today`,
            product_id: product.product_id,
            movement_type: 'ENTRADA - REPOSIÇÃO (24H)',
            event_kind: 'stock_in',
            quantity: restockQty,
            event_at: dateIso,
            event_at_raw: `${dateLocal} ${eventDate.toLocaleTimeString('pt-BR')}`,
            nf_key: `352610${Math.floor(1000000000 + Math.random() * 9000000000)}`,
            recorded_at: dateIso
          });
        }
      } else if (daysAgo === 1) {
        // Yesterday's sales
        const yestQty = (pIdx === 0 || pIdx === 4 || pIdx === 7 || pIdx === 11 || pIdx === 13)
          ? Math.floor(Math.random() * 12) + 12 // 12 - 23 units
          : Math.floor(Math.random() * 8) + 3;
        
        events.push({
          event_id: `evt-sale-${product.product_id}-yest`,
          product_id: product.product_id,
          movement_type: 'SAÍDA - VENDA',
          event_kind: 'sale',
          quantity: yestQty,
          event_at: dateIso,
          event_at_raw: `${dateLocal} ${eventDate.toLocaleTimeString('pt-BR')}`,
          nf_key: `352610${Math.floor(1000000000 + Math.random() * 9000000000)}`,
          recorded_at: dateIso
        });
      } else {
        // Historical days
        const saleProbability = (pIdx % 3 === 0) ? 0.75 : 0.45;
        if (Math.random() < saleProbability) {
          const qty = Math.floor(Math.random() * 8) + 1;
          events.push({
            event_id: `evt-sale-${product.product_id}-${daysAgo}`,
            product_id: product.product_id,
            movement_type: 'SAÍDA - VENDA',
            event_kind: 'sale',
            quantity: qty,
            event_at: dateIso,
            event_at_raw: `${dateLocal} ${eventDate.toLocaleTimeString('pt-BR')}`,
            nf_key: `352610${Math.floor(1000000000 + Math.random() * 9000000000)}`,
            recorded_at: dateIso
          });
        }

        if (daysAgo % 9 === 0 && Math.random() < 0.6) {
          const restockQty = Math.floor(Math.random() * 40) + 15;
          events.push({
            event_id: `evt-in-${product.product_id}-${daysAgo}`,
            product_id: product.product_id,
            movement_type: 'ENTRADA - REPOSIÇÃO',
            event_kind: 'stock_in',
            quantity: restockQty,
            event_at: dateIso,
            event_at_raw: `${dateLocal} ${eventDate.toLocaleTimeString('pt-BR')}`,
            nf_key: `352609${Math.floor(1000000000 + Math.random() * 9000000000)}`,
            recorded_at: dateIso
          });
        }
      }
    }
  });

  return events;
}
