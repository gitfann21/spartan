from .base import Op
from .node import Node
import numpy as np

class OuterProductExpr(Op, Node):
  _members = ['children', 'map_fn', 'map_fn_kw', 'reduce_fn', 'reduce_fn_kw']
  
def outer_product(a, b, map_fn, reduce_fn):
  return OuterProductExpr(a, b, map_fn, reduce_fn)

def outer(a, b):
  return OuterProductExpr(a, b, map_fn=np.dot, 
                          reduce_fn=np.add)
