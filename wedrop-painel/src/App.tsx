import { useState, useMemo, useCallback, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { MetricSummary } from './components/MetricSummary';
import { CategoryStrip } from './components/CategoryStrip';
import { WithoutStatusExpander } from './components/WithoutStatusExpander';
import { CategoryDetailView } from './components/CategoryDetailView';
import { OverviewCharts } from './components/OverviewCharts';
import { DailyDecisionDashboard } from './components/DailyDecisionDashboard';
import { DayComparisonView } from './components/DayComparisonView';
import { PriceFluctuationView } from './components/PriceFluctuationView';
import { SettingsModal } from './components/SettingsModal';
import { ProductDetailModal } from './components/ProductDetailModal';
import { dataService } from './services/dataService';
import { ProductRecord, ThemeId, DashboardViewMode, DataSourceConfig } from './types/wedrop';
import { getLocalDateString, formatDateBR } from './utils/status';

const THEME_STORAGE_KEY = 'wedrop_theme_id';

export function App() {
  // Theme state: defaults to light-wedrop or saved theme
  const [currentTheme, setCurrentTheme] = useState<ThemeId>(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY) as ThemeId | null;
    return saved || 'light-wedrop';
  });

  // Apply theme class to document.body
  useEffect(() => {
    document.body.className = `theme-${currentTheme}`;
    localStorage.setItem(THEME_STORAGE_KEY, currentTheme);
  }, [currentTheme]);

  // View Mode: 'decision_24h' (default), 'day_comparison', 'price_alerts', 'full_catalog'
  const [viewMode, setViewMode] = useState<DashboardViewMode>('decision_24h');

  // Date range state: opens on today only, like the Streamlit sidebar
  const [startDate, setStartDate] = useState<string>(() => getLocalDateString());
  const [endDate, setEndDate] = useState<string>(() => getLocalDateString());
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Modals state
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedProductDetails, setSelectedProductDetails] = useState<ProductRecord | null>(null);
  const [forceWithoutStatusOpen, setForceWithoutStatusOpen] = useState(false);

  // Data loading state
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [config, setConfig] = useState<DataSourceConfig>(() => dataService.getConfig());
  const [dataVersion, setDataVersion] = useState(0);

  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    await dataService.loadFromApi();
    setConfig(dataService.getConfig());
    setDataVersion((v) => v + 1);
    setIsRefreshing(false);
    setIsLoading(false);
  }, []);

  // Leitura ao abrir o painel. A coleta roda às 00:00; depois disso, o botão Atualizar relê o Supabase.
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 24H Decision Analysis Data (D0 vs D-1)
  const decision24hData = useMemo(() => {
    return dataService.get24hDecisionData();
  }, [dataVersion]);

  // Data queries based on startDate, endDate, and dataVersion
  const categorySummaries = useMemo(() => {
    return dataService.getCategoryActivity(startDate, endDate);
  }, [startDate, endDate, dataVersion]);

  const dailyActivity = useMemo(() => {
    return dataService.getDailyActivity(startDate, endDate, selectedCategory);
  }, [startDate, endDate, selectedCategory, dataVersion]);

  const topProductsDaily = useMemo(() => {
    return dataService.getTopProductsDaily(startDate, endDate, selectedCategory, 100);
  }, [startDate, endDate, selectedCategory, dataVersion]);

  const topProductsOverall = useMemo(() => {
    return dataService.getTopProductsOverall(startDate, endDate, 20);
  }, [startDate, endDate, dataVersion]);

  const productsWithoutStatus = useMemo(() => {
    return dataService.getProductsWithoutStatus();
  }, [dataVersion]);

  const categoryProductsWithActivity = useMemo(() => {
    if (!selectedCategory) return [];
    return dataService.getProductsForCategory(selectedCategory, startDate, endDate);
  }, [selectedCategory, startDate, endDate, dataVersion]);

  // Totals for top metric summary
  const totals = useMemo(() => {
    const activeProducts = categorySummaries.reduce((acc, c) => acc + c.active_products, 0);
    const inactiveProducts = categorySummaries.reduce((acc, c) => acc + c.inactive_products, 0);
    const withoutStatus = categorySummaries.reduce((acc, c) => acc + c.products_without_status, 0);
    const unitsSold = categorySummaries.reduce((acc, c) => acc + c.units_sold, 0);
    const unitsRestocked = categorySummaries.reduce((acc, c) => acc + c.units_restocked, 0);

    return {
      activeProducts,
      inactiveProducts,
      withoutStatus,
      unitsSold,
      unitsRestocked,
    };
  }, [categorySummaries]);

  const isSingleDay = startDate === endDate;
  const productsCount = dataService.getProductsCount();
  const showContent = !isLoading && (config.isConnected || productsCount > 0);

  // Export CSV
  const handleExportData = useCallback(() => {
    const prods = dataService.getProductsList();
    if (!prods.length) return;

    const headers = [
      'product_id',
      'name',
      'category',
      'sku',
      'price',
      'previous_price',
      'is_active',
      'stock',
      'real_balance',
      'supplier',
      'url',
    ];
    const rows = prods.map((p) => [
      p.product_id,
      `"${p.name.replace(/"/g, '""')}"`,
      p.category,
      p.sku || '',
      `"${p.price || ''}"`,
      `"${p.previous_price || ''}"`,
      p.is_active || '',
      p.stock || '',
      p.real_balance || '',
      `"${p.supplier || ''}"`,
      p.url,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `wedrop_relatorio_${startDate}_${endDate}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [startDate, endDate]);

  const selectedCategorySummary = useMemo(() => {
    if (!selectedCategory) return null;
    return categorySummaries.find((c) => c.name === selectedCategory) || null;
  }, [selectedCategory, categorySummaries]);

  const handleSelectCategoryFromView = (catName: string) => {
    setSelectedCategory(catName);
    setViewMode('full_catalog');
  };

  return (
    <div className="min-h-screen bg-app text-theme flex flex-col font-sans transition-colors">
      {/* Top Navbar with Theme Switcher & View Modes */}
      <Navbar
        config={config}
        currentTheme={currentTheme}
        onSelectTheme={setCurrentTheme}
        viewMode={viewMode}
        onChangeViewMode={setViewMode}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onExportData={handleExportData}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Area: 100% full-width responsive without dead margins */}
      <div className="flex-1 flex flex-col lg:flex-row w-full min-w-0">
        {/* Left Sidebar */}
        <Sidebar
          startDate={startDate}
          endDate={endDate}
          onChangeStartDate={setStartDate}
          onChangeEndDate={setEndDate}
          selectedCategory={selectedCategory}
          onSelectCategory={(cat) => {
            setSelectedCategory(cat);
            if (cat) setViewMode('full_catalog');
          }}
          totalProductsCount={productsCount}
          dataSourceName={config.isConnected ? 'Supabase' : 'Indisponível'}
        />

        {/* Dashboard Main Workspace - 100% fluid edge-to-edge */}
        <main className="flex-1 p-2.5 sm:p-4 lg:p-6 min-w-0 w-full overflow-hidden">
          {/* Header Title & Date Range Caption */}
          <div className="mb-6 border-b border-theme/50 pb-4">
            <h1 className="text-2xl sm:text-3xl font-black text-theme tracking-tight">
              Monitoramento diário WeDrop
            </h1>
            <p className="text-xs text-muted mt-1 font-medium">
              Período analisado: <strong className="text-theme">{formatDateBR(startDate)}</strong> a{' '}
              <strong className="text-theme">{formatDateBR(endDate)}</strong> ·{' '}
              {config.statusMessage}
            </p>
          </div>

          {isLoading && (
            <div className="py-16 text-center text-sm text-muted">Carregando dados do Supabase...</div>
          )}

          {!isLoading && !config.isConnected && (
            <div className="mb-6 p-3 rounded-lg border border-red-300 dark:border-red-900 bg-red-50 dark:bg-red-950/30 text-xs font-semibold text-red-700 dark:text-red-300">
              {config.statusMessage}
            </div>
          )}

          {!isLoading && config.isConnected && productsCount === 0 && (
            <div className="mb-6 p-3 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 text-xs font-semibold text-amber-800 dark:text-amber-300">
              Ainda não há produtos carregados. Os dados chegam com a coleta diária.
            </div>
          )}

          {showContent && (
            <>
              {/* Metric Summary Top Strip */}
              <MetricSummary
                categoriesCount={categorySummaries.length}
                activeProducts={totals.activeProducts}
                inactiveProducts={totals.inactiveProducts}
                withoutStatusProducts={totals.withoutStatus}
                unitsSold={totals.unitsSold}
                unitsRestocked={totals.unitsRestocked}
                isSingleDay={isSingleDay}
                onOpenWithoutStatus={() => setForceWithoutStatusOpen(true)}
              />

              {/* Products Without Status Expander (if any) */}
              <WithoutStatusExpander
                products={productsWithoutStatus}
                forceOpen={forceWithoutStatusOpen}
              />

              {/* View Mode Content Render */}
              {viewMode === 'decision_24h' && (
                <DailyDecisionDashboard
                  decisionData={decision24hData}
                  onSelectCategory={handleSelectCategoryFromView}
                  onSelectProductForDetails={setSelectedProductDetails}
                  onNavigateToPrices={() => setViewMode('price_alerts')}
                />
              )}

              {viewMode === 'day_comparison' && (
                <DayComparisonView
                  categoriesComparison={decision24hData.topCategories24h}
                  topProducts={decision24hData.top20Products}
                  onSelectCategory={handleSelectCategoryFromView}
                />
              )}

              {viewMode === 'price_alerts' && (
                <PriceFluctuationView
                  priceChangesUp={decision24hData.priceChangesUp}
                  priceChangesDown={decision24hData.priceChangesDown}
                  onSelectCategory={handleSelectCategoryFromView}
                />
              )}

              {viewMode === 'full_catalog' && (
                <>
                  {/* Category Cards Strip (clickable to filter) */}
                  <CategoryStrip
                    categories={categorySummaries}
                    selectedCategory={selectedCategory}
                    onSelectCategory={setSelectedCategory}
                  />

                  {/* Main View: Category Drill-down OR Overview Charts */}
                  {selectedCategory && selectedCategorySummary ? (
                    <CategoryDetailView
                      category={selectedCategorySummary}
                      products={categoryProductsWithActivity}
                      onBackToOverview={() => setSelectedCategory(null)}
                      onSelectProductForDetails={setSelectedProductDetails}
                    />
                  ) : (
                    <OverviewCharts
                      dailyActivity={dailyActivity}
                      categorySummaries={categorySummaries}
                      topProductsOverall={topProductsOverall}
                      topProductsDaily={topProductsDaily}
                      onSelectCategory={setSelectedCategory}
                      onSelectProductForDetails={setSelectedProductDetails}
                    />
                  )}
                </>
              )}
            </>
          )}
        </main>
      </div>

      {/* Connection & Status Modal (read-only: the key stays on the server) */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        lastCollectionAt={dataService.getLastCollectionAt()}
        categoriesCount={dataService.getCategoriesList().length}
        productsCount={productsCount}
        eventsCount={dataService.getStockEventsList().length}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      {/* Product Detail Datasheet Modal */}
      <ProductDetailModal
        product={selectedProductDetails}
        onClose={() => setSelectedProductDetails(null)}
      />
    </div>
  );
}

export default App;
