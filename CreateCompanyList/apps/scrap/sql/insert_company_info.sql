INSERT INTO companys_info(
	company
	, url
	, employees
	, capital
	, page
	, source
	, add_date
)
SELECT
	{insert_data}
WHERE NOT EXISTS (
	SELECT
		'duplication'
	FROM
		companys_info
	WHERE
		company = '{company}'
		AND url = '{url}'
)
;