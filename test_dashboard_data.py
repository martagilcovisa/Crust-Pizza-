"""Pruebas básicas de integridad: ejecutar con python -m unittest discover -s tests."""
import unittest
from pathlib import Path
from data_utils import load_data,kpis,filter_data,by_dimension

BASE=Path(__file__).resolve().parents[1]/'data'
FILES=['San_Francisco_Crust_Pizza_Ventas.xlsx','San_Francisco_Crust_Pizza_Clientes.xlsx','San_Francisco_Crust_Pizza_Productos.xlsx']

class DashboardDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame,cls.quality=load_data(*( (BASE/n).read_bytes() for n in FILES))
    def test_joins(self):
        self.assertEqual(self.quality['sin_cliente'],0)
        self.assertEqual(self.quality['sin_producto'],0)
        self.assertEqual(self.quality['transacciones_repetidas'],0)
    def test_kpis(self):
        values=kpis(self.frame)
        self.assertEqual(values['transacciones'],45900)
        self.assertEqual(values['clientes'],1000)
        self.assertAlmostEqual(values['ventas'],1357881.66,places=2)
        self.assertAlmostEqual(values['utilidad'],813713.76,places=2)
    def test_filter(self):
        frame=filter_data(self.frame,self.quality['fecha_inicial'],self.quality['fecha_final'],['Dallas'],[],[],[])
        self.assertLess(len(frame),len(self.frame))
        self.assertEqual(set(frame['Ciudad']),{'Dallas'})
        self.assertAlmostEqual(kpis(frame)['ventas'],330545.67,places=2)
    def test_branch_group_total(self):
        grouped=by_dimension(self.frame,'Sucursal')
        self.assertEqual(len(grouped),8)
        self.assertAlmostEqual(grouped['VentaNeta'].sum(),1357881.66,places=2)

if __name__=='__main__':unittest.main()
