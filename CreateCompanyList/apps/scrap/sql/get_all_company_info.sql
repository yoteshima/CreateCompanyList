SELECT
	company
	, url
	, source
	, DATE_FORMAT(add_date, '%Y/%m/%d') AS add_date
FROM
	companys_info
ORDER BY
	company
	, add_date
;