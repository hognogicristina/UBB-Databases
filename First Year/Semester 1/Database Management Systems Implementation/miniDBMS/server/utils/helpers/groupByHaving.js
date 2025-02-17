function applyGroupBy(results, groupByColumns, selectColumns) {
  const groupedResults = {};

  results.forEach((row) => {
    const groupKey = groupByColumns.map((col) => row[col]).join('||');

    if (!groupedResults[groupKey]) {
      groupedResults[groupKey] = {
        __rows: [],
        ...Object.fromEntries(Object.keys(row).map((key) => [key, row[key]])),
        __count: 0,
      };
    }
    groupedResults[groupKey].__rows.push(row);
    groupedResults[groupKey].__count += 1;
  });

  return Object.values(groupedResults).map((group) => {
    const aggregatedRow = {...group}

    selectColumns.forEach((col) => {
      if (col.toLowerCase().startsWith('count(')) {
        aggregatedRow[col] = group.__count;
      } else if (col.toLowerCase().startsWith('avg(')) {
        const colName = col.match(/\((.+)\)/)[1];
        const values = group.__rows.map((row) => parseFloat(row[colName])).filter((v) => !isNaN(v));
        aggregatedRow[col] = values.reduce((sum, val) => sum + val, 0) / values.length || null;
      } else if (col.toLowerCase().startsWith('sum(')) {
        const colName = col.match(/\((.+)\)/)[1];
        const values = group.__rows.map((row) => parseFloat(row[colName])).filter((v) => !isNaN(v));
        aggregatedRow[col] = values.reduce((sum, val) => sum + val, 0) || null;
      } else if (col.toLowerCase().startsWith('max(')) {
        const colName = col.match(/\((.+)\)/)[1];
        const values = group.__rows.map((row) => parseFloat(row[colName])).filter((v) => !isNaN(v));
        aggregatedRow[col] = Math.max(...values) || null;
      } else if (col.toLowerCase().startsWith('min(')) {
        const colName = col.match(/\((.+)\)/)[1];
        const values = group.__rows.map((row) => parseFloat(row[colName])).filter((v) => !isNaN(v));
        aggregatedRow[col] = Math.min(...values) || null;
      } else if (!groupByColumns.includes(col)) {
        aggregatedRow[col] = group.__rows[0][col];
      }
    });

    return aggregatedRow;
  });
}

function applyHaving(groupedResults, havingConditions) {
  return groupedResults.filter((group) =>
    havingConditions.every((cond) => {
      const {aggregateFunction, attribute, operator, value} = cond;

      let aggregateValue;
      const values = group.__rows.map((row) => parseFloat(row[attribute])).filter((v) => !isNaN(v));

      switch (aggregateFunction) {
        case 'count':
          aggregateValue = values.length;
          break;
        case 'avg':
          aggregateValue = values.reduce((sum, val) => sum + val, 0) / values.length || null;
          break;
        case 'sum':
          aggregateValue = values.reduce((sum, val) => sum + val, 0) || null;
          break;
        case 'max':
          aggregateValue = Math.max(...values) || null;
          break;
        case 'min':
          aggregateValue = Math.min(...values) || null;
          break;
        default:
          throw new Error(`Unsupported aggregate function: ${aggregateFunction}`);
      }

      switch (operator) {
        case '=':
          return aggregateValue === value;
        case '>':
          return aggregateValue > value;
        case '>=':
          return aggregateValue >= value;
        case '<':
          return aggregateValue < value;
        case '<=':
          return aggregateValue <= value;
        default:
          return false;
      }
    })
  );
}

function applyOrderBy(results, orderByClause) {
  if (!orderByClause || orderByClause.length === 0) {
    return results;
  }

  const orderCriteria = orderByClause.map((order) => {
    const [column, direction] = order.trim().split(/\s+/);
    return {
      column,
      direction: direction ? direction.toLowerCase() : 'asc',
    };
  });

  return results.sort((a, b) => {
    for (const {column, direction} of orderCriteria) {
      const aValue = a[column];
      const bValue = b[column];

      if (aValue == null || bValue == null) {
        continue;
      }

      if (aValue < bValue) {
        return direction === 'asc' ? -1 : 1;
      } else if (aValue > bValue) {
        return direction === 'asc' ? 1 : -1;
      }
    }

    return 0;
  });
}


module.exports = {applyGroupBy, applyHaving, applyOrderBy};