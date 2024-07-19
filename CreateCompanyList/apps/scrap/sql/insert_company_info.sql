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
		'exists'
	FROM
		companys_info
	WHERE
		company = '{company}'
		OR url = '{url}'
)
;