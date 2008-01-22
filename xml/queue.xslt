<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<!-- TODO:  1) links
			2) proper dates with http://www.djkaty.com/drupal/xsl-date-time -->

<xsl:template match="/queue">
<html><head><title>PLD builder queue</title></head><body>
<xsl:for-each select="group">
	<xsl:sort select="@no" order="descending"/>
	<p><b><xsl:value-of select="@no"/></b>. <xsl:value-of select="time"/> from <xsl:value-of select="requester"/><xsl:text> </xsl:text><small><xsl:value-of select="@id"/>, <xsl:value-of select="priority"/>, <xsl:value-of select="@flags"/></small><br/>
	<ul>
	<xsl:for-each select="batch">
	<li>
		<xsl:value-of select="src-rpm"/> 
		(<xsl:value-of select="spec"/> -R <xsl:value-of select="branch"/> 
		<xsl:for-each select="with | without">
			<xsl:if test="name() = 'with'">
				<xsl:text> --with </xsl:text>
			</xsl:if>
			<xsl:if test="name() = 'without'">
				<xsl:text> --without </xsl:text>
			</xsl:if>
			<xsl:value-of select="."/>
			<xsl:if test="position() != last()">
				<xsl:text> </xsl:text>
			</xsl:if>
		</xsl:for-each>
		<xsl:if test="kernel">
			<xsl:text> --define 'alt_kernel </xsl:text>
			<xsl:value-of select="kernel"/>'
		</xsl:if>)
		<small>
			[<xsl:for-each select="builder"><b>
				<xsl:choose>
					<xsl:when test="@status = 'OK'">
						<font color='green'><xsl:value-of select="."/>:<xsl:value-of select="@status"/></font>
					</xsl:when>
					<xsl:when test="@status = 'FAIL'">
						<font color='red'><xsl:value-of select="."/>:<xsl:value-of select="@status"/></font>
					</xsl:when>
					<xsl:otherwise>
						<font color='black'><xsl:value-of select="."/>:<xsl:value-of select="@status"/></font>
					</xsl:otherwise>
				</xsl:choose>
			</b>
				<xsl:if test="position()!=last()"><xsl:text> </xsl:text></xsl:if>
				</xsl:for-each>]
		</small>
	</li>
	</xsl:for-each>
	</ul>
</p>
</xsl:for-each>
</body></html>
</xsl:template>

</xsl:stylesheet>

