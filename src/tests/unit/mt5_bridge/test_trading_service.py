#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla TradingService, w szczególności dla rozszerzonych funkcji handlowych.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import sys
import os
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import testowanych modułów
from src.mt5_bridge.trading_service import TradingService
from src.mt5_bridge.mt5_connector import MT5Connector


class TestTradingServiceAdvanced(unittest.TestCase):
    """Testy dla zaawansowanych funkcji handlowych w TradingService."""
    
    def setUp(self):
        """Setup środowiska testowego przed każdym testem."""
        self.mock_connector = Mock()
        self.trading_service = TradingService(self.mock_connector)
        
        # Mockowanie get_open_positions żeby zwracać listę zamiast Mock
        self.patch_get_positions = patch.object(
            self.trading_service, 'get_open_positions'
        )
        self.mock_get_positions = self.patch_get_positions.start()
        self.mock_get_positions.return_value = []
        
        # Dodatkowy patch dla risk_manager - bezpośrednio w metodzie apply_trailing_stop
        self.risk_manager_patch = patch('src.risk_management.risk_manager.get_risk_manager')
        self.mock_risk_manager = MagicMock()
        self.mock_get_risk_manager = self.risk_manager_patch.start()
        self.mock_get_risk_manager.return_value = self.mock_risk_manager
        
    def tearDown(self):
        """Cleanup po testach."""
        self.patch_get_positions.stop()
        self.risk_manager_patch.stop()
    
    def test_apply_trailing_stop_success(self):
        """Test aplikacji trailing stop z pozytywnym rezultatem."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            market_data = {
                'symbol': 'EURUSD',
                'bid': 1.1050,
                'ask': 1.1052,
                'spread': 0.0002
            }
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1050,
                'ask': 1.1052
            }
            
            # Mockowanie podjęcia decyzji przez risk_manager
            self.mock_risk_manager.should_adjust_trailing_stop.return_value = (True, 1.1000)
            
            # Mockowanie modyfikacji pozycji
            self.mock_connector.modify_position.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.apply_trailing_stop(12345)
            
            # Sprawdzenie rezultatu
            self.assertTrue(result)
            
            # Sprawdzenie, czy odpowiednie metody zostały wywołane
            mock_get_positions.assert_called_once()
            self.mock_connector.get_symbol_info.assert_called_once_with('EURUSD')
            self.mock_risk_manager.should_adjust_trailing_stop.assert_called_once()
            self.mock_connector.modify_position.assert_called_once()
    
    def test_apply_trailing_stop_no_adjustment(self):
        """Test aplikacji trailing stop bez konieczności dostosowania."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            market_data = {
                'symbol': 'EURUSD',
                'bid': 1.1020,
                'ask': 1.1022
            }
            self.mock_connector.get_market_data.return_value = market_data
            
            # Mockowanie podjęcia decyzji przez risk_manager - brak potrzeby dostosowania
            self.mock_risk_manager.should_adjust_trailing_stop.return_value = (False, None)
            
            # Wywołanie testowanej metody
            result = self.trading_service.apply_trailing_stop(12345)
            
            # Sprawdzenie rezultatu
            self.assertFalse(result)
            
            # Sprawdzenie, czy modify_position nie zostało wywołane
            self.mock_connector.modify_position.assert_not_called()
    
    def test_update_trailing_stops_multiple_positions(self):
        """Test aktualizacji trailing stop dla wielu pozycji."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                },
                {
                    'ticket': 12346,
                    'symbol': 'GBPUSD',
                    'type': 'sell',
                    'volume': 0.1,
                    'open_price': 1.3000,
                    'sl': 1.3050,
                    'tp': 1.2900
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie apply_trailing_stop
            with patch.object(self.trading_service, 'apply_trailing_stop') as mock_apply:
                # Pierwszy zwraca True, drugi False (jeden dostosowany, drugi nie)
                mock_apply.side_effect = [True, False]
                
                # Wywołanie testowanej metody
                result = self.trading_service.update_trailing_stops()
                
                # Sprawdzenie rezultatu
                self.assertEqual(len(result['updated']), 1)
                self.assertEqual(len(result['unchanged']), 1)
                self.assertEqual(len(result['errors']), 0)
                
                # Sprawdzenie, czy apply_trailing_stop zostało wywołane dla obu pozycji
                self.assertEqual(mock_apply.call_count, 2)
                mock_apply.assert_any_call(12345)
                mock_apply.assert_any_call(12346)
    
    def test_partial_close_success(self):
        """Test częściowego zamknięcia pozycji."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.5,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie close_position_partial
            self.mock_connector.close_position_partial.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.partial_close(12345, 0.5)
            
            # Sprawdzenie rezultatu
            self.assertTrue(result)
            
            # Sprawdzenie, czy odpowiednie metody zostały wywołane
            mock_get_positions.assert_called_once()
            self.mock_connector.close_position_partial.assert_called_once_with(12345, 0.25)  # 0.5 * 0.5 = 0.25
    
    def test_partial_close_invalid_volume(self):
        """Test częściowego zamknięcia z nieprawidłowym wolumenem."""
        # Wywołanie testowanej metody z nieprawidłowym wolumenem
        result = self.trading_service.partial_close(12345, 1.5)  # > 1
        
        # Sprawdzenie rezultatu
        self.assertFalse(result)
        
        # Close_position_partial nie powinno być wywołane
        self.mock_connector.close_position_partial.assert_not_called()
    
    def test_create_oco_order_success(self):
        """Test tworzenia zlecenia OCO (One-Cancels-the-Other)."""
        # Mockowanie place_pending_order dla dwóch zleceń
        self.mock_connector.place_pending_order.side_effect = [
            {'success': True, 'ticket': 12345},
            {'success': True, 'ticket': 12346}
        ]
        
        # Wywołanie testowanej metody
        result = self.trading_service.create_oco_order(
            symbol='EURUSD',
            order_type='buy_stop',
            volume=0.1,
            price=1.1100,
            sl=1.1050,
            tp=1.1200,
            opposite_price=1.0900
        )
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['main_ticket'], 12345)
        self.assertEqual(result['opposite_ticket'], 12346)
        
        # Sprawdzenie, czy place_pending_order zostało wywołane dla obu zleceń
        self.assertEqual(self.mock_connector.place_pending_order.call_count, 2)
        
        # Sprawdzenie argumentów dla pierwszego zlecenia
        first_call_args = self.mock_connector.place_pending_order.call_args_list[0][1]
        self.assertEqual(first_call_args['symbol'], 'EURUSD')
        self.assertEqual(first_call_args['order_type'], 'buy_stop')
        self.assertEqual(first_call_args['price'], 1.1100)
        
        # Sprawdzenie argumentów dla drugiego zlecenia
        second_call_args = self.mock_connector.place_pending_order.call_args_list[1][1]
        self.assertEqual(second_call_args['symbol'], 'EURUSD')
        self.assertEqual(second_call_args['order_type'], 'sell_stop')
        self.assertEqual(second_call_args['price'], 1.0900)
    
    def test_create_oco_order_first_fails(self):
        """Test tworzenia zlecenia OCO gdy pierwsze zlecenie nie udaje się."""
        # Mockowanie place_pending_order - pierwsze zlecenie nie udaje się
        self.mock_connector.place_pending_order.return_value = {
            'success': False,
            'error': 'Invalid price'
        }
        
        # Wywołanie testowanej metody
        result = self.trading_service.create_oco_order(
            symbol='EURUSD',
            order_type='buy_stop',
            volume=0.1,
            price=1.1100,
            sl=1.1050,
            tp=1.1200,
            opposite_price=1.0900
        )
        
        # Sprawdzenie rezultatu
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid price')
        
        # Sprawdzenie, czy place_pending_order zostało wywołane tylko raz
        self.mock_connector.place_pending_order.assert_called_once()
    
    def test_set_breakeven_stop_success(self):
        """
        Test sprawdzający, czy break-even stop jest poprawnie ustawiany, gdy jest wystarczający zysk.
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.1000,
            'volume': 0.1,
            'sl': 1.0950,
            'tp': 1.1100
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1040, 'ask': 1.1042, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Mock modify_position
        self.mock_connector.modify_position.return_value = True
        
        # Wywołaj metodę
        result = self.trading_service.set_breakeven_stop(123456, 30)
        
        # Sprawdź rezultaty
        self.assertTrue(result)
        
        # Sprawdź, czy wywołano modify_position z odpowiednimi parametrami
        self.mock_connector.modify_position.assert_called_with({
            'ticket': 123456,
            'symbol': 'EURUSD',
            'sl': 1.1000,  # Poziom wejścia
            'tp': 1.1100
        })
        
        self.patch_get_market_data.stop()
    
    def test_set_breakeven_stop_not_enough_profit(self):
        """
        Test sprawdzający, czy break-even stop nie jest ustawiany gdy nie ma wystarczającego zysku.
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.1000,
            'volume': 0.1,
            'sl': 1.0950,
            'tp': 1.1100
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1020, 'ask': 1.1022, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Wywołaj metodę
        result = self.trading_service.set_breakeven_stop(123456, 30)
        
        # Sprawdź, czy nie wywołano modify_position (zysk tylko 20 pipsów, wymagane 30)
        self.assertFalse(result)
        self.mock_connector.modify_position.assert_not_called()
        
        self.patch_get_market_data.stop()
    
    def test_apply_advanced_trailing_stop_fixed_pips(self):
        """Test aplikacji zaawansowanego trailing stop z strategią fixed_pips."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1050,  # 50 pipsów zysku
                'ask': 1.1052
            }
            
            # Mockowanie modyfikacji pozycji
            self.mock_connector.modify_position.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.apply_advanced_trailing_stop(
                12345, 
                strategy='fixed_pips',
                params={'activation_pips': 30, 'step_pips': 15}
            )
            
            # Sprawdzenie rezultatu
            self.assertTrue(result)
            
            # Sprawdzenie, czy modify_position zostało wywołane z odpowiednimi parametrami
            self.mock_connector.modify_position.assert_called_once()
            call_args = self.mock_connector.modify_position.call_args[0][0]
            self.assertEqual(call_args['ticket'], 12345)
            self.assertAlmostEqual(call_args['sl'], 1.1050 - 0.0015, places=5)  # Nowy SL na poziomie cena - 15 pipsów
    
    def test_apply_advanced_trailing_stop_percent(self):
        """Test aplikacji zaawansowanego trailing stop z strategią percent."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1110,  # 1% zysku
                'ask': 1.1112
            }
            
            # Mockowanie modyfikacji pozycji
            self.mock_connector.modify_position.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.apply_advanced_trailing_stop(
                12345, 
                strategy='percent',
                params={'activation_percent': 0.8, 'step_percent': 0.2}
            )
            
            # Sprawdzenie rezultatu
            self.assertTrue(result)
            
            # Sprawdzenie, czy modify_position zostało wywołane z odpowiednimi parametrami
            self.mock_connector.modify_position.assert_called_once()
            call_args = self.mock_connector.modify_position.call_args[0][0]
            self.assertEqual(call_args['ticket'], 12345)
            self.assertAlmostEqual(call_args['sl'], 1.1110 * (1 - 0.2/100), places=5)  # Nowy SL na poziomie cena * (1 - 0.2%)
    
    def test_update_advanced_trailing_stops(self):
        """Test aktualizacji zaawansowanych trailing stopów dla wielu pozycji."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.1,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                },
                {
                    'ticket': 12346,
                    'symbol': 'GBPUSD',
                    'type': 'sell',
                    'volume': 0.1,
                    'open_price': 1.3000,
                    'sl': 1.3050,
                    'tp': 1.2900
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie apply_advanced_trailing_stop
            with patch.object(self.trading_service, 'apply_advanced_trailing_stop') as mock_apply:
                # Pierwszy zwraca True, drugi False (jeden dostosowany, drugi nie)
                mock_apply.side_effect = [True, False]
                
                # Wywołanie testowanej metody
                result = self.trading_service.update_advanced_trailing_stops(
                    strategy='fixed_pips',
                    params={'activation_pips': 30, 'step_pips': 15}
                )
                
                # Sprawdzenie rezultatu
                self.assertEqual(len(result['updated']), 1)
                self.assertEqual(len(result['unchanged']), 1)
                self.assertEqual(len(result['errors']), 0)
                
                # Sprawdzenie, czy apply_advanced_trailing_stop zostało wywołane dla obu pozycji
                self.assertEqual(mock_apply.call_count, 2)
                # Sprawdzenie, czy parametry zostały przekazane
                mock_apply.assert_any_call(12345, 'fixed_pips', {'activation_pips': 30, 'step_pips': 15})
                mock_apply.assert_any_call(12346, 'fixed_pips', {'activation_pips': 30, 'step_pips': 15})
    
    def test_advanced_partial_close_fixed_percent(self):
        """Test zaawansowanego częściowego zamknięcia pozycji z strategią fixed_percent."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.5,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1030,  # 30 pipsów zysku
                'ask': 1.1032
            }
            
            # Mockowanie close_position_partial
            self.mock_connector.close_position_partial.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.advanced_partial_close(
                12345, 
                strategy='fixed_percent',
                params={'percent': 0.3}  # 30%
            )
            
            # Sprawdzenie rezultatu
            self.assertTrue(result['success'])
            self.assertEqual(result['closed_volume'], 0.15)  # 0.5 * 0.3 = 0.15
            self.assertEqual(result['remaining_volume'], 0.35)  # 0.5 - 0.15 = 0.35
            self.assertEqual(result['closed_percent'], 0.3)
            
            # Sprawdzenie, czy odpowiednie metody zostały wywołane
            mock_get_positions.assert_called_once()
            self.mock_connector.get_symbol_info.assert_called_once()
            self.mock_connector.close_position_partial.assert_called_once_with(12345, 0.15)
    
    def test_advanced_partial_close_fixed_lots(self):
        """Test zaawansowanego częściowego zamknięcia pozycji z strategią fixed_lots."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.5,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1030,  # 30 pipsów zysku
                'ask': 1.1032
            }
            
            # Mockowanie close_position_partial
            self.mock_connector.close_position_partial.return_value = True
            
            # Wywołanie testowanej metody
            result = self.trading_service.advanced_partial_close(
                12345, 
                strategy='fixed_lots',
                params={'lots': 0.2}  # 0.2 lota
            )
            
            # Sprawdzenie rezultatu
            self.assertTrue(result['success'])
            self.assertEqual(result['closed_volume'], 0.2)
            self.assertEqual(result['remaining_volume'], 0.3)  # 0.5 - 0.2 = 0.3
            self.assertEqual(result['closed_percent'], 0.2/0.5)  # 40%
            
            # Sprawdzenie, czy odpowiednie metody zostały wywołane
            mock_get_positions.assert_called_once()
            self.mock_connector.get_symbol_info.assert_called_once()
            self.mock_connector.close_position_partial.assert_called_once_with(12345, 0.2)
    
    def test_advanced_partial_close_take_profit_levels(self):
        """Test zaawansowanego częściowego zamknięcia pozycji z strategią take_profit_levels."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.5,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie danych rynkowych
            self.mock_connector.get_symbol_info.return_value = {
                'bid': 1.1040,  # 40 pipsów zysku
                'ask': 1.1042
            }
            
            # Mockowanie close_position_partial
            self.mock_connector.close_position_partial.return_value = True
            
            # Poziomy take profit
            levels = [
                {'profit_pips': 20, 'percent': 0.3},  # zamknij 30% pozycji po 20 pipsach zysku
                {'profit_pips': 40, 'percent': 0.5},  # zamknij 50% pozycji po 40 pipsach zysku
                {'profit_pips': 60, 'percent': 0.7}   # zamknij 70% pozycji po 60 pipsach zysku
            ]
            
            # Wywołanie testowanej metody
            result = self.trading_service.advanced_partial_close(
                12345, 
                strategy='take_profit_levels',
                params={'levels': levels}
            )
            
            # Sprawdzenie rezultatu
            self.assertTrue(result['success'])
            self.assertEqual(result['closed_volume'], 0.25)  # 0.5 * 0.5 = 0.25
            self.assertEqual(result['remaining_volume'], 0.25)  # 0.5 - 0.25 = 0.25
            self.assertEqual(result['closed_percent'], 0.5)  # 50%
            self.assertEqual(result['achieved_level'], levels[1])  # drugi poziom (40 pipsów)
            
            # Sprawdzenie, czy odpowiednie metody zostały wywołane
            mock_get_positions.assert_called_once()
            self.mock_connector.get_symbol_info.assert_called_once()
            self.mock_connector.close_position_partial.assert_called_once_with(12345, 0.25)
    
    def test_manage_take_profits(self):
        """Test automatycznego zarządzania częściowym zamykaniem pozycji po określonych poziomach zysku."""
        # Patchowanie metody get_open_positions w TradingService
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            # Mockowanie danych potrzebnych do testu
            positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 'buy',
                    'volume': 0.5,
                    'open_price': 1.1000,
                    'sl': 1.0950,
                    'tp': 1.1100
                },
                {
                    'ticket': 12346,
                    'symbol': 'GBPUSD',
                    'type': 'sell',
                    'volume': 0.3,
                    'open_price': 1.3000,
                    'sl': 1.3050,
                    'tp': 1.2900
                }
            ]
            mock_get_positions.return_value = positions
            
            # Mockowanie advanced_partial_close
            with patch.object(self.trading_service, 'advanced_partial_close') as mock_partial_close:
                # Pierwszy zwraca sukces, drugi zwraca informację o nieosiągniętym poziomie
                mock_partial_close.side_effect = [
                    {
                        'success': True,
                        'closed_volume': 0.15,
                        'remaining_volume': 0.35,
                        'closed_percent': 0.3,
                        'current_profit_pips': 30,
                        'achieved_level': {'profit_pips': 20, 'percent': 0.3},
                        'message': "Pozycja 12345 częściowo zamknięta. Zamknięto: 0.15 lotów."
                    },
                    {
                        'success': False,
                        'closed_volume': 0,
                        'remaining_volume': 0.3,
                        'closed_percent': 0,
                        'current_profit_pips': 10,
                        'message': "Nie osiągnięto żadnego poziomu zysku. Aktualny zysk: 10 pips"
                    }
                ]
                
                # Konfiguracja poziomów take profit
                take_profit_config = {
                    'default_levels': [
                        {'profit_pips': 20, 'percent': 0.3},
                        {'profit_pips': 50, 'percent': 0.5},
                        {'profit_pips': 100, 'percent': 0.7}
                    ],
                    'symbol_levels': {
                        'EURUSD': [
                            {'profit_pips': 15, 'percent': 0.25},
                            {'profit_pips': 30, 'percent': 0.5}
                        ]
                    }
                }
                
                # Wywołanie testowanej metody
                result = self.trading_service.manage_take_profits(take_profit_config)
                
                # Sprawdzenie rezultatu
                self.assertEqual(len(result['closed']), 1)
                self.assertEqual(len(result['unchanged']), 1)
                self.assertEqual(len(result['errors']), 0)
                
                # Sprawdzenie, czy advanced_partial_close zostało wywołane dwa razy
                self.assertEqual(mock_partial_close.call_count, 2)
    
    def test_cancel_oco_pair(self):
        """Test anulowania pary zleceń OCO."""
        # Symulacja istniejącej pary OCO
        self.trading_service.oco_pairs = {
            "12345_12346": {
                'oco_pair_id': "12345_12346",
                'symbol': 'EURUSD',
                'created_at': datetime.now(),
                'status': 'active',
                'orders': {
                    'main': {
                        'ticket': 12345,
                        'type': 'buy_stop',
                        'price': 1.1100,
                        'status': 'pending'
                    },
                    'opposite': {
                        'ticket': 12346,
                        'type': 'sell_stop',
                        'price': 1.0900,
                        'status': 'pending'
                    }
                },
                'volume': 0.1,
                'sl': 1.1050,
                'tp': 1.1200
            }
        }
        
        # Mockowanie delete_pending_order
        self.mock_connector.delete_pending_order.side_effect = [True, True]
        
        # Wywołanie testowanej metody
        result = self.trading_service.cancel_oco_pair("12345_12346")
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['oco_pair_id'], "12345_12346")
        self.assertTrue(result['main_cancelled'])
        self.assertTrue(result['opposite_cancelled'])
        
        # Sprawdzenie, czy delete_pending_order zostało wywołane dla obu zleceń
        self.assertEqual(self.mock_connector.delete_pending_order.call_count, 2)
        self.mock_connector.delete_pending_order.assert_any_call(12345)
        self.mock_connector.delete_pending_order.assert_any_call(12346)
        
        # Sprawdzenie, czy status pary OCO został zaktualizowany
        oco_pair = self.trading_service.oco_pairs["12345_12346"]
        self.assertEqual(oco_pair['status'], 'cancelled')
        self.assertEqual(oco_pair['orders']['main']['status'], 'cancelled')
        self.assertEqual(oco_pair['orders']['opposite']['status'], 'cancelled')
    
    def test_handle_oco_activation(self):
        """Test obsługi aktywacji jednego z zleceń OCO."""
        # Symulacja istniejącej pary OCO
        self.trading_service.oco_pairs = {
            "12345_12346": {
                'oco_pair_id': "12345_12346",
                'symbol': 'EURUSD',
                'created_at': datetime.now(),
                'status': 'active',
                'orders': {
                    'main': {
                        'ticket': 12345,
                        'type': 'buy_stop',
                        'price': 1.1100,
                        'status': 'pending'
                    },
                    'opposite': {
                        'ticket': 12346,
                        'type': 'sell_stop',
                        'price': 1.0900,
                        'status': 'pending'
                    }
                },
                'volume': 0.1,
                'sl': 1.1050,
                'tp': 1.1200
            }
        }
        
        # Mockowanie delete_pending_order - drugie zlecenie zostanie anulowane
        self.mock_connector.delete_pending_order.return_value = True
        
        # Wywołanie testowanej metody - aktywacja pierwszego zlecenia (main)
        result = self.trading_service.handle_oco_activation(12345)
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['oco_pair_id'], "12345_12346")
        self.assertEqual(result['activated_ticket'], 12345)
        self.assertEqual(result['cancelled_ticket'], 12346)
        self.assertTrue(result['cancelled_success'])
        
        # Sprawdzenie, czy delete_pending_order zostało wywołane dla drugiego zlecenia
        self.mock_connector.delete_pending_order.assert_called_once_with(12346)
        
        # Sprawdzenie, czy status pary OCO został zaktualizowany
        oco_pair = self.trading_service.oco_pairs["12345_12346"]
        self.assertEqual(oco_pair['status'], 'triggered')
        self.assertEqual(oco_pair['orders']['main']['status'], 'triggered')
        self.assertEqual(oco_pair['orders']['opposite']['status'], 'cancelled')
    
    def test_monitor_oco_orders(self):
        """Test monitorowania par zleceń OCO."""
        # Symulacja istniejących par OCO
        self.trading_service.oco_pairs = {
            "12345_12346": {
                'oco_pair_id': "12345_12346",
                'symbol': 'EURUSD',
                'created_at': datetime.now(),
                'status': 'active',
                'orders': {
                    'main': {
                        'ticket': 12345,
                        'type': 'buy_stop',
                        'price': 1.1100,
                        'status': 'pending'
                    },
                    'opposite': {
                        'ticket': 12346,
                        'type': 'sell_stop',
                        'price': 1.0900,
                        'status': 'pending'
                    }
                },
                'volume': 0.1,
                'sl': 1.1050,
                'tp': 1.1200
            },
            "12347_12348": {
                'oco_pair_id': "12347_12348",
                'symbol': 'GBPUSD',
                'created_at': datetime.now(),
                'status': 'active',
                'orders': {
                    'main': {
                        'ticket': 12347,
                        'type': 'buy_stop',
                        'price': 1.3100,
                        'status': 'pending'
                    },
                    'opposite': {
                        'ticket': 12348,
                        'type': 'sell_stop',
                        'price': 1.2900,
                        'status': 'pending'
                    }
                },
                'volume': 0.1,
                'sl': 1.3050,
                'tp': 1.3200
            }
        }
        
        # Patchowanie metod get_open_positions i get_pending_orders
        with patch.object(self.trading_service, 'get_open_positions') as mock_get_positions:
            with patch.object(self.trading_service, 'get_pending_orders') as mock_get_orders:
                # Główne zlecenie pierwszej pary zostało aktywowane (jest w pozycjach, nie ma w oczekujących)
                # Druga para nadal jest w oczekujących
                mock_get_positions.return_value = [
                    {'ticket': 12345, 'symbol': 'EURUSD', 'type': 'buy', 'volume': 0.1}
                ]
                mock_get_orders.return_value = [
                    {'ticket': 12346, 'symbol': 'EURUSD', 'type': 'sell_stop', 'volume': 0.1},
                    {'ticket': 12347, 'symbol': 'GBPUSD', 'type': 'buy_stop', 'volume': 0.1},
                    {'ticket': 12348, 'symbol': 'GBPUSD', 'type': 'sell_stop', 'volume': 0.1}
                ]
                
                # Patchowanie handle_oco_activation
                with patch.object(self.trading_service, 'handle_oco_activation') as mock_handle_activation:
                    mock_handle_activation.return_value = {
                        'success': True,
                        'oco_pair_id': "12345_12346",
                        'activated_ticket': 12345,
                        'cancelled_ticket': 12346,
                        'cancelled_success': True
                    }
                    
                    # Wywołanie testowanej metody
                    result = self.trading_service.monitor_oco_orders()
                    
                    # Sprawdzenie rezultatu
                    self.assertEqual(result['active_pairs'], 2)
                    self.assertEqual(result['processed_pairs'], 1)
                    self.assertEqual(len(result['activated']), 1)
                    self.assertEqual(len(result['cancelled']), 0)
                    self.assertEqual(len(result['errors']), 0)
                    
                    # Sprawdzenie, czy handle_oco_activation zostało wywołane dla aktywowanego zlecenia
                    mock_handle_activation.assert_called_once_with(12345)

    def test_advanced_breakeven_stop_standard(self):
        """
        Test sprawdzający działanie standardowej strategii break-even stop.
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.1000,
            'volume': 0.1,
            'sl': 1.0950,
            'tp': 1.1100
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1040, 'ask': 1.1042, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Wywołaj metodę
        self.mock_connector.modify_position.return_value = True
        result = self.trading_service.advanced_breakeven_stop(
            123456,
            strategy='standard',
            params={'profit_pips': 30}
        )
        
        # Sprawdź rezultaty
        self.assertTrue(result['success'])
        self.assertEqual(result['new_sl'], 1.1000)  # Poziom wejścia
        self.assertAlmostEqual(result['current_profit_pips'], 40.0, places=2)  # 40 pipsów zysku
        
        # Sprawdź, czy wywołano modify_position z odpowiednimi parametrami
        self.mock_connector.modify_position.assert_called_with({
            'ticket': 123456,
            'symbol': 'EURUSD',
            'sl': 1.1000,
            'tp': 1.1100
        })
        
        self.patch_get_market_data.stop()
        
    def test_advanced_breakeven_stop_lock_profit(self):
        """
        Test sprawdzający działanie strategii break-even stop z zabezpieczeniem zysku (lock profit).
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'sell',
            'open_price': 1.1100,
            'volume': 0.1,
            'sl': 1.1150,
            'tp': 1.1000
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1048, 'ask': 1.1050, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Wywołaj metodę
        self.mock_connector.modify_position.return_value = True
        result = self.trading_service.advanced_breakeven_stop(
            123456,
            strategy='lock_profit',
            params={'profit_pips': 30, 'lock_pips': 10}
        )
        
        # Sprawdź rezultaty
        self.assertTrue(result['success'])
        self.assertEqual(result['new_sl'], 1.1090)  # Poziom wejścia - lock_pips
        self.assertAlmostEqual(result['current_profit_pips'], 50.0, places=2)  # 50 pipsów zysku
        
        # Sprawdź, czy wywołano modify_position z odpowiednimi parametrami
        self.mock_connector.modify_position.assert_called_with({
            'ticket': 123456,
            'symbol': 'EURUSD',
            'sl': 1.1090,
            'tp': 1.1000
        })
        
        self.patch_get_market_data.stop()
    
    def test_advanced_breakeven_stop_partial(self):
        """
        Test sprawdzający działanie strategii break-even stop z częściowym zamknięciem pozycji.
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.1000,
            'volume': 0.1,
            'sl': 1.0950,
            'tp': 1.1100
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1040, 'ask': 1.1042, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Mock partial_close
        self.patch_partial_close = patch.object(
            self.trading_service, 'partial_close', return_value=True
        )
        self.mock_partial_close = self.patch_partial_close.start()
        
        # Wywołaj metodę
        self.mock_connector.modify_position.return_value = True
        result = self.trading_service.advanced_breakeven_stop(
            123456,
            strategy='partial',
            params={'profit_pips': 30, 'volume_percent': 0.5}
        )
        
        # Sprawdź rezultaty
        self.assertTrue(result['success'])
        self.assertEqual(result['new_sl'], 1.1000)  # Poziom wejścia
        self.assertAlmostEqual(result['current_profit_pips'], 40.0, places=2)  # 40 pipsów zysku
        self.assertTrue(result.get('partial_close', False))
        
        # Sprawdź, czy wywołano modify_position z odpowiednimi parametrami
        self.mock_connector.modify_position.assert_called_with({
            'ticket': 123456,
            'symbol': 'EURUSD',
            'sl': 1.1000,
            'tp': 1.1100
        })
        
        # Sprawdź, czy wywołano partial_close z odpowiednimi parametrami
        self.mock_partial_close.assert_called_with(123456, 0.5)
        
        self.patch_get_market_data.stop()
        self.patch_partial_close.stop()
    
    def test_advanced_breakeven_stop_tiered(self):
        """
        Test sprawdzający działanie strategii break-even stop z poziomami (tiered).
        """
        # Mock get_open_positions
        position = {
            'ticket': 123456,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.1000,
            'volume': 0.1,
            'sl': 1.0950,
            'tp': 1.1100
        }
        self.mock_get_positions.return_value = [position]
        
        # Mock get_market_data
        market_data = {'bid': 1.1065, 'ask': 1.1067, 'spread': 2}
        self.patch_get_market_data = patch.object(
            self.trading_service, 'get_market_data', return_value=market_data
        )
        self.mock_get_market_data = self.patch_get_market_data.start()
        
        # Poziomy dla strategii tiered
        levels = [
            {'profit_pips': 30, 'sl_pips': 0},   # na poziomie wejścia
            {'profit_pips': 50, 'sl_pips': 10},  # 10 pipsów powyżej wejścia
            {'profit_pips': 80, 'sl_pips': 20}   # 20 pipsów powyżej wejścia
        ]
        
        # Wywołaj metodę
        self.mock_connector.modify_position.return_value = True
        result = self.trading_service.advanced_breakeven_stop(
            123456,
            strategy='tiered',
            params={'levels': levels}
        )
        
        # Sprawdź rezultaty
        self.assertTrue(result['success'])
        self.assertEqual(result['new_sl'], 1.1010)  # Poziom wejścia + 10 pipsów (osiągnięty poziom 50 pipsów)
        self.assertAlmostEqual(result['current_profit_pips'], 65.0, places=2)  # 65 pipsów zysku
        self.assertEqual(result['achieved_level'], {'profit_pips': 50, 'sl_pips': 10})
        
        # Sprawdź, czy wywołano modify_position z odpowiednimi parametrami
        self.mock_connector.modify_position.assert_called_with({
            'ticket': 123456,
            'symbol': 'EURUSD',
            'sl': 1.1010,
            'tp': 1.1100
        })
        
        self.patch_get_market_data.stop()
    
    def test_manage_breakeven_stops(self):
        """
        Test sprawdzający działanie funkcji zarządzania break-even stops dla wszystkich pozycji.
        """
        # Mock get_open_positions
        positions = [
            {
                'ticket': 123456,
                'symbol': 'EURUSD',
                'type': 'buy',
                'open_price': 1.1000,
                'volume': 0.1,
                'sl': 1.0950,
                'tp': 1.1100
            },
            {
                'ticket': 234567,
                'symbol': 'GBPUSD',
                'type': 'sell',
                'open_price': 1.2500,
                'volume': 0.1,
                'sl': 1.2550,
                'tp': 1.2400
            },
            {
                'ticket': 345678,
                'symbol': 'USDJPY',
                'type': 'buy',
                'open_price': 145.00,
                'volume': 0.1,
                'sl': 144.50,
                'tp': 146.00
            }
        ]
        self.mock_get_positions.return_value = positions
        
        # Mock advanced_breakeven_stop
        self.patch_advanced_breakeven = patch.object(
            self.trading_service, 
            'advanced_breakeven_stop',
            side_effect=[
                # Dla EURUSD - sukces
                {
                    'success': True,
                    'message': "Ustawiono standard break-even dla pozycji 123456",
                    'ticket': 123456,
                    'current_profit_pips': 40.0,
                    'strategy': 'standard',
                    'new_sl': 1.1000
                },
                # Dla GBPUSD - brak wymaganego zysku
                {
                    'success': False,
                    'message': "Nie osiągnięto wymaganego zysku dla pozycji 234567. Aktualny zysk: 20.0 pipsów",
                    'ticket': 234567,
                    'current_profit_pips': 20.0,
                    'strategy': 'lock_profit',
                    'new_sl': None
                },
                # Dla USDJPY - błąd
                {
                    'success': False,
                    'message': "Nie udało się zmodyfikować pozycji 345678",
                    'ticket': 345678,
                    'current_profit_pips': 35.0,
                    'strategy': 'standard',
                    'new_sl': 145.00
                }
            ]
        )
        self.mock_advanced_breakeven = self.patch_advanced_breakeven.start()
        
        # Konfiguracja break-even
        breakeven_config = {
            'default': {
                'strategy': 'standard',
                'params': {'profit_pips': 30}
            },
            'symbol_config': {
                'GBPUSD': {
                    'strategy': 'lock_profit',
                    'params': {'profit_pips': 25, 'lock_pips': 5}
                }
            }
        }
        
        # Wywołaj metodę
        result = self.trading_service.manage_breakeven_stops(breakeven_config)
        
        # Sprawdź rezultaty
        self.assertEqual(len(result['modified']), 1)
        self.assertEqual(len(result['unchanged']), 1)
        self.assertEqual(len(result['errors']), 1)
        
        # Sprawdź, czy advanced_breakeven_stop został wywołany dla każdej pozycji
        self.assertEqual(self.mock_advanced_breakeven.call_count, 3)
        
        # Sprawdź wywołania dla poszczególnych pozycji
        calls = [
            call(123456, strategy='standard', params={'profit_pips': 30}),
            call(234567, strategy='lock_profit', params={'profit_pips': 25, 'lock_pips': 5}),
            call(345678, strategy='standard', params={'profit_pips': 30})
        ]
        self.mock_advanced_breakeven.assert_has_calls(calls, any_order=True)
        
        self.patch_advanced_breakeven.stop()


if __name__ == '__main__':
    unittest.main() 