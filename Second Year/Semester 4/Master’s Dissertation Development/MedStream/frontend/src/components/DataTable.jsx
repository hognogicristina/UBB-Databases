import {useCallback, useEffect, useState} from "react"
import {Pagination, Select} from "@cloudscape-design/components"
import LoadingSpinner from "./LoadingSpinner.jsx"
import {INPUT_LIMITS, limitText} from "../utils/inputLimits.js"

function getSelectedOption(options, value) {
  return options.find((option) => String(option.value) === String(value)) || null
}

export default function DataTable({
                                    items,
                                    loading = false,
                                    loadingMessage = "Loading data...",
                                    emptyMessage = "No records found.",
                                    pageSize = 10,
                                    sortOptions = [],
                                    defaultSort,
                                    filters = [],
                                    getItemKey,
                                    renderHeader,
                                    renderRow,
                                    rowClassName,
                                    bodyClassName = "medstream-data-table-body",
                                    shellClassName = "medstream-data-table-shell",
                                    controlsLayoutClassName,
                                    bottomControls,
                                    simplePagination = false,
                                  }) {
  const pageSizeOptions = [5, 10, 15, 25]
  const buildInitialFilterValues = useCallback(() =>
    Object.fromEntries(
      filters.map((filter) => [filter.id, filter.defaultValue ?? (filter.type === "text" ? "" : "all")]),
    ), [filters])
  const filterSignature = filters.map((filter) => filter.id).join("|")
  const [currentPage, setCurrentPage] = useState(1)
  const [sortOrder, setSortOrder] = useState(defaultSort ?? sortOptions[0]?.value ?? "")
  const [filterValues, setFilterValues] = useState(() => buildInitialFilterValues())
  const [activePageSize, setActivePageSize] = useState(pageSize)

  useEffect(() => {
    const nextDefaults = buildInitialFilterValues()

    setFilterValues((current) => {
      const nextValues = {...nextDefaults, ...current}
      const isSame = Object.keys(nextValues).every((key) => nextValues[key] === current[key])
      return isSame ? current : nextValues
    })
  }, [buildInitialFilterValues, filterSignature])

  useEffect(() => {
    if (!sortOptions.some((option) => option.value === sortOrder)) {
      setSortOrder(defaultSort ?? sortOptions[0]?.value ?? "")
    }
  }, [defaultSort, sortOptions, sortOrder])

  useEffect(() => {
    setActivePageSize(pageSize)
  }, [pageSize])

  const filteredItems = items.filter((item) =>
    filters.every((filter) => filter.matches(item, filterValues[filter.id] ?? filter.defaultValue ?? "")),
  )

  const activeSort = sortOptions.find((option) => option.value === sortOrder)
  const sortedItems = activeSort ? [...filteredItems].sort(activeSort.compare) : filteredItems
  const maxPage = Math.max(1, Math.ceil(sortedItems.length / activePageSize))
  const paginatedItems = sortedItems.slice((currentPage - 1) * activePageSize, currentPage * activePageSize)

  useEffect(() => {
    if (currentPage > maxPage) {
      setCurrentPage(maxPage)
    }
  }, [currentPage, maxPage])

  useEffect(() => {
    setCurrentPage(1)
  }, [sortOrder, filterValues, activePageSize])

  return (
    <>
      <div className={controlsLayoutClassName ?? "medstream-data-table-controls"}>
        {filters.map((filter) => (
          <div key={filter.id}>
            <label className="medstream-data-table-label" htmlFor={filter.id}>
              {filter.label}
            </label>
            {filter.type === "text" ? (
              <input
                id={filter.id}
                type="text"
                value={filterValues[filter.id] ?? ""}
                onChange={(event) => {
                  const value = limitText(event.target.value, filter.maxLength ?? INPUT_LIMITS.search)
                  setFilterValues((current) => ({...current, [filter.id]: value}))
                  filter.onChange?.(value)
                }}
                placeholder={filter.placeholder}
                disabled={filter.disabled}
                maxLength={filter.maxLength ?? INPUT_LIMITS.search}
                className="console-input medstream-data-table-input"
              />
            ) : (
              <Select
                selectedOption={getSelectedOption(filter.options, filterValues[filter.id] ?? filter.defaultValue ?? "all")}
                onChange={({detail}) => {
                  const value = detail.selectedOption.value
                  setFilterValues((current) => ({...current, [filter.id]: value}))
                  filter.onChange?.(value)
                }}
                options={filter.options}
                placeholder={filter.placeholder}
                disabled={filter.disabled}
                selectedAriaLabel={`Selected ${filter.label}`}
              />
            )}
          </div>
        ))}

        {sortOptions.length > 0 && (
          <div>
            <label className="medstream-data-table-label" htmlFor="dataTableSort">
              Sort Order
            </label>
            <Select
              selectedOption={getSelectedOption(sortOptions, sortOrder)}
              onChange={({detail}) => setSortOrder(detail.selectedOption.value)}
              options={sortOptions}
              selectedAriaLabel="Selected sort order"
            />
          </div>
        )}

        <div>
          <label className="medstream-data-table-label" htmlFor="dataTablePageSize">
            Page Size
          </label>
          <Select
            selectedOption={getSelectedOption(pageSizeOptions.map((option) => ({label: String(option), value: String(option)})), activePageSize)}
            onChange={({detail}) => setActivePageSize(Number(detail.selectedOption.value))}
            options={pageSizeOptions.map((option) => ({label: String(option), value: String(option)}))}
            selectedAriaLabel="Selected page size"
          />
        </div>
      </div>

      {loading ? (
        <LoadingSpinner text={loadingMessage}/>
      ) : (
        <div className={shellClassName}>
          {renderHeader?.()}

          {paginatedItems.length === 0 && (
            <div className="medstream-data-table-empty-state">
              {emptyMessage}
            </div>
          )}

          {paginatedItems.length > 0 && (
            <div className={bodyClassName}>
              {paginatedItems.map((item) => (
                <div key={getItemKey(item)} className={rowClassName?.(item)}>
                  {renderRow(item)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="medstream-data-table-footer">
        <div className="medstream-data-table-bottom-controls">
          {bottomControls}
        </div>
        <Pagination
          currentPageIndex={currentPage}
          pagesCount={maxPage}
          onChange={({detail}) => setCurrentPage(detail.currentPageIndex)}
          openEnd={simplePagination}
        />
      </div>
    </>
  )
}
