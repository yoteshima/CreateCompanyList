SELECT
	company
	, url
	, source
	, capital
	, employees
	, DATE_FORMAT(add_date, '%Y/%m/%d') AS add_date
FROM
	companys_info
WHERE
	source = 'Fuma'
ORDER BY
	add_date
	, company
;