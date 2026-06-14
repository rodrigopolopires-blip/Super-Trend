"""
Super Trend Automation Strategy
Automação de Trading com Super Trend
Parâmetros: Multiplicador 18, Fator 1.8, Stop Loss 500 pontos
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SuperTrendStrategy:
    """Classe para implementar a estratégia Super Trend com automação"""
    
    def __init__(self, period=18, multiplier=1.8, stop_loss=500):
        """
        Inicializa a estratégia
        
        Args:
            period (int): Período para cálculo do ATR (padrão 18)
            multiplier (float): Multiplicador do ATR (padrão 1.8)
            stop_loss (int): Stop loss em pontos (padrão 500)
        """
        self.period = period
        self.multiplier = multiplier
        self.stop_loss = stop_loss
        self.position = None
        self.entry_price = None
        self.upper_band = None
        self.lower_band = None
        
        logger.info(f"Strategy initialized - Period: {period}, Multiplier: {multiplier}, Stop Loss: {stop_loss}")
    
    def calculate_atr(self, df, period=None):
        """
        Calcula o Average True Range (ATR)
        
        Args:
            df (DataFrame): DataFrame com colunas 'high', 'low', 'close'
            period (int): Período para cálculo
            
        Returns:
            Series: Valores de ATR
        """
        if period is None:
            period = self.period
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calcular True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def calculate_super_trend(self, df):
        """
        Calcula o Super Trend
        
        Args:
            df (DataFrame): DataFrame com OHLC
            
        Returns:
            DataFrame: DataFrame com Super Trend bands
        """
        # Calcular HL2 (High-Low)/2
        hl2 = (df['high'] + df['low']) / 2
        
        # Calcular ATR
        atr = self.calculate_atr(df)
        
        # Calcular bandas básicas
        basic_ub = hl2 + self.multiplier * atr
        basic_lb = hl2 - self.multiplier * atr
        
        # Calcular bandas finais
        upper_band = np.zeros(len(df))
        lower_band = np.zeros(len(df))
        supertrend = np.zeros(len(df))
        
        for i in range(self.period, len(df)):
            # Upper Band
            upper_band[i] = basic_ub.iloc[i]
            if i > 0:
                if basic_ub.iloc[i] < upper_band[i-1] or df['close'].iloc[i-1] > upper_band[i-1]:
                    upper_band[i] = basic_ub.iloc[i]
                else:
                    upper_band[i] = upper_band[i-1]
            
            # Lower Band
            lower_band[i] = basic_lb.iloc[i]
            if i > 0:
                if basic_lb.iloc[i] > lower_band[i-1] or df['close'].iloc[i-1] < lower_band[i-1]:
                    lower_band[i] = basic_lb.iloc[i]
                else:
                    lower_band[i] = lower_band[i-1]
            
            # Super Trend
            if i == 0:
                supertrend[i] = lower_band[i]
            else:
                if supertrend[i-1] == lower_band[i-1]:
                    supertrend[i] = lower_band[i] if df['close'].iloc[i] > lower_band[i] else upper_band[i]
                else:
                    supertrend[i] = upper_band[i] if df['close'].iloc[i] < upper_band[i] else lower_band[i]
        
        df['upper_band'] = upper_band
        df['lower_band'] = lower_band
        df['supertrend'] = supertrend
        df['atr'] = atr
        
        return df
    
    def check_signals(self, df):
        """
        Verifica sinais de compra e venda
        
        Args:
            df (DataFrame): DataFrame com Super Trend calculado
            
        Returns:
            dict: Sinais de compra/venda
        """
        current_price = df['close'].iloc[-1]
        previous_price = df['close'].iloc[-2]
        
        current_st = df['supertrend'].iloc[-1]
        previous_st = df['supertrend'].iloc[-2]
        
        current_upper = df['upper_band'].iloc[-1]
        current_lower = df['lower_band'].iloc[-1]
        
        signals = {
            'buy': False,
            'sell': False,
            'current_price': current_price,
            'supertrend': current_st,
            'upper_band': current_upper,
            'lower_band': current_lower,
            'signal_strength': None
        }
        
        # Sinal de COMPRA: preço cruza acima da banda inferior
        if previous_price <= df['supertrend'].iloc[-2] and current_price > current_st:
            signals['buy'] = True
            signals['signal_strength'] = 'FORTE' if current_price > current_lower else 'FRACO'
            logger.info(f"🟢 SINAL DE COMPRA - Preço: {current_price:.2f}, SuperTrend: {current_st:.2f}")
        
        # Sinal de VENDA: preço cruza abaixo da banda superior
        elif previous_price >= df['supertrend'].iloc[-2] and current_price < current_st:
            signals['sell'] = True
            signals['signal_strength'] = 'FORTE' if current_price < current_upper else 'FRACO'
            logger.info(f"🔴 SINAL DE VENDA - Preço: {current_price:.2f}, SuperTrend: {current_st:.2f}")
        
        return signals
    
    def calculate_stop_loss(self, entry_price, position_type):
        """
        Calcula o stop loss baseado na entrada
        
        Args:
            entry_price (float): Preço de entrada
            position_type (str): 'compra' ou 'venda'
            
        Returns:
            float: Preço do stop loss
        """
        if position_type.lower() == 'compra':
            stop_loss_price = entry_price - self.stop_loss
        else:  # venda
            stop_loss_price = entry_price + self.stop_loss
        
        return stop_loss_price
    
    def execute_trade(self, signal, current_price):
        """
        Executa a operação de trading
        
        Args:
            signal (dict): Dicionário com sinais
            current_price (float): Preço atual
            
        Returns:
            dict: Resultado da execução
        """
        execution_result = {
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,
            'executed': False,
            'position_type': None,
            'entry_price': None,
            'stop_loss': None,
            'message': ''
        }
        
        if signal['buy'] and self.position is None:
            self.position = 'COMPRADO'
            self.entry_price = current_price
            stop_loss = self.calculate_stop_loss(current_price, 'compra')
            
            execution_result['executed'] = True
            execution_result['position_type'] = 'COMPRA'
            execution_result['entry_price'] = current_price
            execution_result['stop_loss'] = stop_loss
            execution_result['message'] = f"✅ COMPRA EXECUTADA - Entrada: {current_price:.2f}, Stop Loss: {stop_loss:.2f}"
            
            logger.info(execution_result['message'])
            logger.info(f"   Take Profit sugerido: {current_price + self.stop_loss:.2f}")
        
        elif signal['sell'] and self.position == 'COMPRADO':
            profit = current_price - self.entry_price
            profit_pct = (profit / self.entry_price) * 100
            
            execution_result['executed'] = True
            execution_result['position_type'] = 'VENDA'
            execution_result['entry_price'] = self.entry_price
            execution_result['current_price'] = current_price
            execution_result['profit'] = profit
            execution_result['profit_pct'] = profit_pct
            execution_result['message'] = f"✅ VENDA EXECUTADA - Saída: {current_price:.2f}, Lucro: {profit:.2f} ({profit_pct:.2f}%)"
            
            logger.info(execution_result['message'])
            
            self.position = None
            self.entry_price = None
        
        return execution_result
    
    def check_stop_loss(self, current_price):
        """
        Verifica se o stop loss foi acionado
        
        Args:
            current_price (float): Preço atual
            
        Returns:
            bool: True se stop loss foi acionado
        """
        if self.position == 'COMPRADO' and self.entry_price:
            stop_loss_price = self.calculate_stop_loss(self.entry_price, 'compra')
            
            if current_price <= stop_loss_price:
                loss = current_price - self.entry_price
                loss_pct = (loss / self.entry_price) * 100
                
                logger.warning(f"⚠️ STOP LOSS ACIONADO - Saída: {current_price:.2f}, Perda: {loss:.2f} ({loss_pct:.2f}%)")
                
                self.position = None
                self.entry_price = None
                
                return True
        
        return False
    
    def process_candle(self, df):
        """
        Processa uma vela completa
        
        Args:
            df (DataFrame): DataFrame com dados OHLC
        """
        # Calcular Super Trend
        df = self.calculate_super_trend(df)
        
        # Verificar sinais
        signals = self.check_signals(df)
        
        # Verificar stop loss
        current_price = df['close'].iloc[-1]
        if self.check_stop_loss(current_price):
            self.position = None
        
        # Executar trade se houver sinal
        if signals['buy'] or signals['sell']:
            self.execute_trade(signals, current_price)


def load_market_data(csv_path):
    """
    Carrega dados de mercado de um arquivo CSV
    
    Args:
        csv_path (str): Caminho do arquivo CSV
        
    Returns:
        DataFrame: DataFrame com dados OHLC
    """
    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.lower()
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV deve conter as colunas: {required_cols}")
        
        df['datetime'] = pd.to_datetime(df.get('datetime', df.get('date', pd.date_range(periods=len(df)))))
        df = df.sort_values('datetime').reset_index(drop=True)
        
        logger.info(f"✅ Dados carregados: {len(df)} candles")
        return df
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados: {str(e)}")
        return None


def main():
    """Função principal - Exemplo de uso"""
    
    logger.info("=" * 60)
    logger.info("SUPER TREND AUTOMATION - Iniciando...")
    logger.info("=" * 60)
    logger.info(f"Parâmetros: Período=18, Multiplicador=1.8, Stop Loss=500 pontos")
    logger.info("=" * 60)
    
    # Criar instância da estratégia
    strategy = SuperTrendStrategy(period=18, multiplier=1.8, stop_loss=500)
    
    # Exemplo: Carregar dados (substitua pelo seu arquivo CSV)
    # df = load_market_data('market_data.csv')
    
    # Exemplo com dados fictícios para teste
    logger.info("\n📊 Modo Demo - Gerando dados fictícios para teste...")
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    np.random.seed(42)
    close_prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': close_prices + np.random.randn(100) * 50,
        'high': close_prices + abs(np.random.randn(100)) * 100,
        'low': close_prices - abs(np.random.randn(100)) * 100,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Processar cada candle
    logger.info("\n🚀 Processando candles...\n")
    
    for i in range(18, len(df)):
        current_df = df.iloc[:i+1].copy()
        strategy.process_candle(current_df)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Automação completada!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
