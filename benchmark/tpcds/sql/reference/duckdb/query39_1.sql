-- TPC-DS query 39 (formulation 1) — DuckDB; unique public output aliases only.
-- Presentation revision: public-output-contract-v1; re-freeze Gold before use.
--
-- Upstream / 상류 출처: StarRocks/starrocks @ 9d288306166d
--   fe/fe-core/src/test/resources/sql/tpcds/query39-1.sql
--   License / 라이선스: Apache-2.0
-- Adaptation / 변환: date_add(cast('d' as date), n) -> (cast('d' as date) \+/- n); ORDER BY alias 'lochierarchy' expanded to its defining expression (q36/q70/q86)
--
-- TPC-DS is a trademark of the Transaction Processing Performance Council.
-- This is a TPC-DS derived workload, not an audited TPC benchmark result.
-- figures produced with it are not comparable to published TPC-DS results.
-- TPC-DS는 TPC의 상표입니다. 본 파일은 TPC-DS 파생 워크로드이며 공인된 TPC
-- 벤치마크 결과가 아닙니다. 측정값은 공표된 TPC-DS 결과와 비교할 수 없습니다.
--
-- query 39-1
with inv as
(select w_warehouse_name,w_warehouse_sk,i_item_sk,d_moy
       ,stdev,mean, case mean when 0 then null else stdev/mean end cov
 from(select w_warehouse_name,w_warehouse_sk,i_item_sk,d_moy
            ,stddev_samp(inv_quantity_on_hand) stdev,avg(inv_quantity_on_hand) mean
      from inventory
          ,item
          ,warehouse
          ,date_dim
      where inv_item_sk = i_item_sk
        and inv_warehouse_sk = w_warehouse_sk
        and inv_date_sk = d_date_sk
        and d_year =2001
      group by w_warehouse_name,w_warehouse_sk,i_item_sk,d_moy) foo
 where case mean when 0 then 0 else stdev/mean end > 1)
select inv1.w_warehouse_sk as month1_warehouse_sk,inv1.i_item_sk as month1_item_sk
        ,inv1.d_moy as month1,inv1.mean as month1_mean,inv1.cov as month1_cov
        ,inv2.w_warehouse_sk as month2_warehouse_sk,inv2.i_item_sk as month2_item_sk
        ,inv2.d_moy as month2,inv2.mean as month2_mean,inv2.cov as month2_cov
from inv inv1,inv inv2
where inv1.i_item_sk = inv2.i_item_sk
  and inv1.w_warehouse_sk =  inv2.w_warehouse_sk
  and inv1.d_moy=1
  and inv2.d_moy=1+1
order by month1_warehouse_sk,month1_item_sk,month1,month1_mean,month1_cov
        ,month2,month2_mean,month2_cov
;
