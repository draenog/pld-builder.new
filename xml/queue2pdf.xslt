<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<!-- TODO:  1) links
			2) proper dates with http://www.djkaty.com/drupal/xsl-date-time -->

<xsl:template match="/queue">

<fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format" font-size="10pt">

<fo:layout-master-set>
    <fo:simple-page-master master-name="A4" page-width="210mm" page-height="297mm" margin="1cm">
  <fo:region-body   margin="0cm"/>
  <fo:region-before extent="0cm"/>
  <fo:region-after  extent="0cm"/>
  <fo:region-start  extent="0cm"/>
  <fo:region-end    extent="0cm"/>
  </fo:simple-page-master>
</fo:layout-master-set>
<fo:page-sequence master-reference="A4">
<fo:flow flow-name="xsl-region-body">


<xsl:for-each select="group">
	<xsl:sort select="@no" order="descending"/>

	<fo:block space-before="2mm" space-after="2mm"><fo:inline font-weight="bold"><xsl:value-of select="@no"/></fo:inline>. <xsl:value-of select="time"/> from <xsl:value-of select="requester"/><xsl:text> </xsl:text><fo:inline font-size="small"><xsl:value-of select="@id"/>, <xsl:value-of select="priority"/>, <xsl:value-of select="@flags"/></fo:inline></fo:block>
	<fo:list-block space-before="2mm" space-after="2mm">
	<xsl:for-each select="batch">
		<fo:list-item space-before="2mm" space-after="2mm">
			<fo:list-item-label start-indent="5mm">
				<fo:block font-family="monospace">*</fo:block>
			</fo:list-item-label>
			<fo:list-item-body start-indent="9mm">
				<fo:block>
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
		<fo:inline font-size="small">
			[<xsl:for-each select="builder">
				<xsl:choose>
					<xsl:when test="@status = 'OK'">
						<fo:inline color="green"><xsl:value-of select="."/>:<xsl:value-of select="@status"/></fo:inline>
					</xsl:when>
					<xsl:when test="@status = 'FAIL'">
						<fo:inline color="red"><xsl:value-of select="."/>:<xsl:value-of select="@status"/></fo:inline>
					</xsl:when>
					<xsl:otherwise>
						<fo:inline color="black"><xsl:value-of select="."/>:<xsl:value-of select="@status"/></fo:inline>
					</xsl:otherwise>
				</xsl:choose>
				<xsl:if test="position()!=last()"><xsl:text> </xsl:text></xsl:if>
				</xsl:for-each>]
			</fo:inline>
			</fo:block>
		</fo:list-item-body>
		</fo:list-item>
	</xsl:for-each>
	</fo:list-block>

</xsl:for-each>

</fo:flow>
</fo:page-sequence>

</fo:root>

</xsl:template>

</xsl:stylesheet>

