-- Annual roll-up files duplicate the monthly files for the same year.
-- Staging must load monthly files only, or every bond is counted twice.
-- Fails (returns rows) if any annual row gets through.

select file_month, count(*) as rows_found
from {{ ref('stg_bond_lodgements') }}
where file_month like '%-annual'
group by file_month
