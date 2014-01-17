from datetime import datetime
import parakeet
import random
import scipy.sparse

import numpy as np
from spartan import expr, util, eager, force
import test_common


def millis(t1, t2):
  dt = t2 - t1
  ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
  return ms

def sparse_multiply(wts, p):  
  for i in range(20):
    util.log_warn('iteration %d begin!', i)
    t1 = datetime.now()
    p = expr.dot(wts, p).force()
    t2 = datetime.now()
    print "iteration %d sparse * dense: %s ms" % (i, millis(t1, t2))
    
  #r = p.glom()
  #print r
  #if scipy.sparse.issparse(r):
  #  print "sparse * sparse: %s ms" % millis(t1, t2)
  #  return r.todense()
  #return r

@util.synchronized
@parakeet.jit
def _build_site_coo(num_pages,
                    num_outlinks,
                    outlinks,
                    site_start,
                    site_end):
  rows = np.zeros((num_pages * num_outlinks,), dtype=np.int32)
  cols = np.empty((num_pages * num_outlinks,), dtype=np.int32)
  data = np.empty((num_pages * num_outlinks,), dtype=np.int32)
  
  i = 0
  for page in xrange(num_pages):
    for link in xrange(num_outlinks):
      rows[i] = outlinks[i]
      cols[i] = page
      data[i] = 1
      i += 1
    
    return rows, cols, data
      
def _make_site_sparse(tile, ex,
                      num_outlinks=None,
                      same_site_prob=None):
  tile_pages = ex.shape[1]
  
  same_site = np.random.rand(num_outlinks * tile_pages) < same_site_prob
  outlink = np.zeros((num_outlinks * tile_pages), dtype=np.int32)
  outlink[same_site] = np.random.randint(ex.ul[1], ex.lr[1], np.count_nonzero(same_site))
  outlink[~same_site] = np.random.randint(0, ex.shape[0], np.count_nonzero(~same_site))
  
  rows, cols, data = _build_site_coo(tile_pages, num_outlinks, outlink, 
                                     ex.ul[1], ex.lr[1])
  
  util.log_warn('Extent: %s, Rows: %s %s', ex, np.min(rows), np.max(rows))
  
  yield ex, scipy.sparse.coo_matrix((data, (rows, cols)),
                                    shape=ex.shape,
                                    dtype=np.float32).tocsr()
                              
#   rows = []
#   cols = []
#   data = []
#   
#   for page in range(ex.shape[1]):
#     for i in range(num_outlinks):
#       if random.random() <= same_site_prob:
#         outlink = random.randrange(ex.ul[1], ex.lr[1])
#       else:
#         outlink = random.randrange(0, ex.shape[0])
# 
#       rows.append(outlink)
#       cols.append(page)
#       data.append(random.random())
#       
#   yield ex, scipy.sparse.coo_matrix((data, (rows, cols)),
#                                  shape=ex.shape,
#                                  dtype=np.float32).tocsr()
  
def pagerank_sparse(num_pages,
                    num_outlinks,
                    same_site_prob,
                    hint):
   
  return expr.shuffle(
           expr.ndarray((num_pages, num_pages), 
                        dtype=np.float32, 
                        tile_hint=hint, 
                        sparse=True),
             fn=_make_site_sparse,
             kw = { 'num_outlinks' : num_outlinks, 
                    'same_site_prob' : same_site_prob })


#@test_common.with_ctx
#Qdef test_pr(ctx):
def benchmark_pr(ctx, timer):
  num_pages = 1000 * 1000 * 50
  num_outlinks = 10
  density = num_outlinks * 1.0 / num_pages
  same_site_prob = 0.9
  col_step = util.divup(num_pages, ctx.num_workers)
  
  wts_tile_hint = [num_pages, col_step]
  p_tile_hint = [col_step, 1]
  #wts = expr.sparse_diagonal((num_pages, num_pages), dtype=np.float32, tile_hint=wts_tile_hint)
  #wts = expr.eager(
  #         expr.sparse_rand((num_pages, num_pages), 
  #                          density=density, 
  #                          format='csr', 
  #                          dtype=np.float32, 
  #                          tile_hint=wts_tile_hint))

  wts = expr.eager(pagerank_sparse(num_pages, num_outlinks, same_site_prob, wts_tile_hint))
  
  #res = wts.glom().todense()
  #for i in range(res.shape[0]):
  #  l = []
  #  for j in range(res.shape[1]):
  #    l.append(round(res[i,j],1))
  #  print l
  #p = expr.sparse_empty((num_pages,1), dtype=np.float32, tile_hint=p_tile_hint).force()
  #for i in range(num_pages):
  #  p[i,0] = 1
  #p = expr.sparse_rand((num_pages, 1), density=1.0, format='csc', dtype=np.float32, tile_hint=p_tile_hint)
  p = expr.eager(expr.rand(num_pages, 1, tile_hint=p_tile_hint).astype(np.float32))
  #q = expr.zeros((num_pages, 1), dtype=np.float32, tile_hint=p_tile_hint).force()
  #q[:] = p.glom().todense()
  #q = expr.lazify(q)
 
  #r = expr.dot(wts, p)
  #print r.glom()
  sparse_multiply(wts, p)
  
  #r2 = sparse_multiply(wts, q)
  #print 'r1:',r1
  #print 'r2:',r2
  #print "r1==r2?", np.all(np.equal(r1, r2))

if __name__ == '__main__':
  test_common.run(__file__)
